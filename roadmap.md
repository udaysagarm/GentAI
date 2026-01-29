# GentAI Roadmap 🚀

## Phase 1: Professional Packaging (Current)
- [ ] Refactor into standard Python package structure (`gentai/` folder).
- [ ] Add `pyproject.toml` configuration.
- [ ] Create `gent` CLI command using entry points.

## Phase 2: The "App Store" Architecture
- [ ] Build `gent install <feature>` logic.
- [ ] Create a "Plugin Registry" (JSON) to host community features.
- [ ] Implement Dynamic Plugin Loading (start without heavy libraries).

## Phase 3: Headless API (The Brain)
- [ ] Decouple Logic from UI.
- [ ] Build FastAPI server to handle requests from any source.
- [ ] Secure API with Authentication.

## Phase 4: World Domination (Clients)
- [ ] Telegram Bot Integration.
- [ ] Mobile App (Flutter/React Native) connecting to API.
- [ ] MacOS Menu Bar App.
- [ ] Global distribution via `pip` and `brew`.
