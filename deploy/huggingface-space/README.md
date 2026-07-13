---
title: AuraOS Sovereign Human-AI Arenas
emoji: 🌀
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: agpl-3.0
short_description: Public interactive AuraOS hackathon demo with Civic, Human Agent, Observatory, and Learning Arenas.
---

# AuraOS — Sovereign Human-AI Arenas

This is the public interactive demonstration of **AuraOS**, a sovereign, local-first cognitive operating substrate that turns human intent into bounded, inspectable, and verifiable Arenas.

## Demonstrated surfaces

- Winnipeg Civic Commons Arena using synthetic demonstration records
- Human Agent Coding Arena with exact topology, evidence gates, and human approval
- Aura Observatory showing how ordinary intent is compiled and routed
- Learning Arena / Crucible for proposal-only learning from verified experience
- Fireworks-first optional model egress when a private `FIREWORKS_API_KEY` Space secret is configured

## Safety and governance

- All Winnipeg civic records are synthetic demonstration data.
- Civic outputs are non-binding and are not legal advice.
- Visual topology, VSA, model output, and stored failed attempts do not grant patch authority.
- The demo does not automatically commit, push, open pull requests, or merge code.
- External model workers are optional and replaceable.
- Human or community authority remains final.

## Source

The Docker image checks out the reviewed AuraOS source at commit:

`611f80b9725a9b6f103e77f2849f6f90ee034836`

Repository: `https://github.com/dallascourchene-commits/AuraOS`

## Optional secrets

Add these through **Space Settings → Variables and secrets → Secrets**. Never place their values in this repository.

- `FIREWORKS_API_KEY`
- `DEEPSEEK_API_KEY` (optional fallback)

The complete deterministic demo remains usable without either secret.
