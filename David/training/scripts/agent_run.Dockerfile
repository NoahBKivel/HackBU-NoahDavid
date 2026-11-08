FROM node:22
RUN npm install -g @anthropic-ai/claude-code
RUN useradd --create-home --uid 1100 runner
USER runner
WORKDIR /work
ENV HOME=/home/runner
