import json
import random

import torch

from intent_training.kevpatch.persistence import random_state, restore_distributed_continuation, trainable_state


def test_distributed_continuation_restores_next_step(tmp_path):
    def make():
        model = torch.nn.Linear(2, 1)
        optimizer = torch.optim.AdamW(model.parameters(), lr=.01)
        scheduler = torch.optim.lr_scheduler.OneCycleLR(optimizer, max_lr=.01, total_steps=5)
        return model, optimizer, scheduler

    def step(model, optimizer, scheduler):
        loss = model(torch.rand(3, 2)).square().mean()
        loss.backward()
        optimizer.step()
        scheduler.step()
        optimizer.zero_grad()
        return loss.detach().clone()

    random.seed(1)
    torch.manual_seed(1)
    model, optimizer, scheduler = make()
    step(model, optimizer, scheduler)
    step(model, optimizer, scheduler)
    saved = tmp_path / 'step-0000002'
    saved.mkdir()
    torch.save({'trainable': trainable_state(model), 'optimizer': optimizer.state_dict(),
                'scheduler': scheduler.state_dict(), 'rng': random_state()}, saved / 'state.pt')
    (tmp_path / 'latest.json').write_text(json.dumps({'step': 2, 'next_global_step': 2,
        'epoch': 0, 'dir': saved.name, 'resume_allowed': False}))
    expected_loss = step(model, optimizer, scheduler)
    expected_weights = trainable_state(model)
    resumed, resumed_optimizer, resumed_scheduler = make()
    restored = restore_distributed_continuation(tmp_path, resumed_optimizer, resumed_scheduler, resumed, 5)
    actual_loss = step(resumed, resumed_optimizer, resumed_scheduler)
    assert restored['step'] == 2
    assert torch.equal(expected_loss, actual_loss)
    assert all(torch.equal(expected_weights[key], value) for key, value in trainable_state(resumed).items())
