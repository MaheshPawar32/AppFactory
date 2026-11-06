# Screen inventory — <app_name>

| Screen | Purpose | Entry point | Primary action | Data source | States | Tests |
|---|---|---|---|---|---|---|
| Splash / launch | Initialize app | App launch | Continue | App config/session | Loading/failure | Startup routing |
| Home | Main overview | Navigation | Main user task | Selected repository | Loading/empty/error/offline | Primary journey |

Replace examples with the actual app. Add every required screen, dialog, sheet and important state before implementation.

## Navigation map
```text
App launch
  -> onboarding (if required)
  -> sign-in (if required)
  -> main shell
      -> feature list
          -> detail
              -> edit / confirmation
```

## Per-screen checklist
- [ ] Purpose and audience
- [ ] Main and secondary actions
- [ ] Data source and persistence
- [ ] Loading, empty, error, offline and success states where relevant
- [ ] Permission-denied behavior where relevant
- [ ] Accessibility labels and focus order
- [ ] Responsive layout
- [ ] Tests
