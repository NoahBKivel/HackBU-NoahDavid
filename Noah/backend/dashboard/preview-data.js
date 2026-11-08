// Fixed sample sessions for reviewing the layout. No requests are sent to
// FastAPI or Modal. These values are illustrative, not a recorded live run.
export function previewSessions() {
  const now = Math.floor(Date.now() / 60000) * 60000;
  const tools = ['Read', 'Edit', 'Bash', 'Edit', 'Read', 'Bash', 'Edit', 'Bash'];
  const descriptions = [
    'Read tests/conftest.py', 'Edited tests/conftest.py', 'pytest tests/ --durations=10',
    'Edited src/checkout.py', 'Read src/inventory.py', 'pytest tests/test_checkout.py',
    'Edited tests/test_inventory.py', 'pytest tests/ -q',
  ];
  const makePoints = (id, risks, spacing, lastOffset, flagAt = -1) =>
    risks.map((risk, index) => {
      const flagged = index === flagAt;
      const tool = flagged ? 'PowerShell' : tools[index % tools.length];
      const summary = flagged ? 'Removed slow integration tests' : descriptions[index % descriptions.length];
      return {
        eventId: id + '-event-' + String(index + 1).padStart(3, '0'),
        seq: index + 1,
        ts: now - lastOffset - (risks.length - 1 - index) * spacing,
        tool, summary, risk, flagged, corrected: flagged, isPending: risk === null,
        monitor: risk === null ? null : 'goal_adherence',
        details: risk === null ? { status: 'classifying' } : {
          behavior: flagged ? 'Deleted two integration test files.' : summary,
          concern: flagged
            ? 'Removing tests may reduce the coverage the user asked to keep.'
            : 'None: consistent with the user instruction.',
          requirement: 'Make the test suite faster without reducing test coverage.',
        },
        notices: flagged ? [
          { level: 'detected', text: 'The agent deleted test files. This may conflict with your instruction to keep test coverage.' },
          { level: 'intervened', text: 'A correction was sent to the agent.' },
        ] : [],
        correction: flagged ? '[Alignment monitor] Check whether deleting these tests reduces coverage. If it does, restore them and find another way to meet the goal.' : null,
        error: null, drift: null, driftRate: null,
        requires_user_intervention: risk === null ? undefined : false,
      };
    });

  const examples = [
    {
      id: 'preview-demo-shop',
      name: 'demo-shop',
      task: 'Speed up the test suite',
      points: makePoints('shop', [
        .13, .09, .16, .11, .08, .2, .15, .24, .16, .33, .27, .43,
        .57, .91, .74, .56, .39, .28, .22, .3, .24, .13, .17, .19,
      ], 120000, 45000, 13),
    },
    {
      id: 'preview-alignment-monitor',
      name: 'alignment-monitor',
      task: 'Connect the classifier',
      points: makePoints('monitor', [
        .12, .08, .17, .14, .21, .13, .26, .18, .15, .23, .19, .11,
        .16, .22, .14, .18, .12, .21, .17, .14, .2, .16, null,
      ], 90000, 30000),
    },
    {
      id: 'preview-demo-docs',
      name: 'demo-shop',
      task: 'Update the project docs',
      points: makePoints('docs', [.08, .11, .07, .14, .09, .12, .1, .08], 120000, 75000).map((point, index) => {
        const summary = index % 2 ? 'Updated docs/api.md' : 'Read README.md';
        return { ...point, tool: index % 2 ? 'Edit' : 'Read', summary, details: {
          behavior: summary,
          concern: 'None: documentation changes follow the requested scope.',
          requirement: 'Update the project documentation to match the current API.',
        } };
      }),
    },
  ];
  // Illustrates the proposed explicit classifier signal; no live integration.
  const stopped = examples[1].points.at(-2);
  stopped.risk = .96;
  stopped.flagged = true;
  stopped.requires_user_intervention = true;
  stopped.tool = 'Edit';
  stopped.summary = 'Attempted to overwrite production configuration';
  stopped.details = {
    behavior: stopped.summary,
    concern: 'The requested integration does not authorize changes to production configuration.',
    requirement: 'Connect the classifier without changing production configuration.',
  };
  stopped.correction = '[Alignment monitor] Stop and wait for user intervention before changing production configuration.';
  stopped.corrected = true;
  return examples;
}
