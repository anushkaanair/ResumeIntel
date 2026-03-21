# Frontend

## Stack
React 18 + TypeScript 5 + Tailwind CSS + Framer Motion

## Structure
- components/ — Reusable UI (Button, Card, ScoreGauge, etc.)
- pages/ — Route-level components
- hooks/ — Custom hooks (useOptimize, useAlignment, etc.)
- lib/ — API client, utils, constants

## Conventions
- Functional components only, hooks for state
- Tailwind utility classes, no CSS modules
- All API calls through lib/api.ts
- Loading/error states for every async operation
- Framer Motion for transitions

## Component Pattern
Every component: named export, props interface, JSDoc description
