# UI reference workflow

1. Place images under `references/<app_name>/<screen_name>.png` where practical.
2. Name each image with the intended screen, for example `home_dashboard.png`.
3. Create a reference mapping: image path → target screen → key visual rules → interactions.
4. Inspect all reference images before implementation.
5. Translate visual structure into real widgets and reusable components.
6. Include responsive behavior and all relevant loading/empty/error/offline states.
7. Compare screenshots at the same viewport size where screenshot tooling is available.
8. Report observed differences and fix the largest issues first.
9. Never claim pixel-perfect visual parity without actually comparing rendered output.
10. Never use a screenshot as a static full-screen image in place of a functional UI unless the user explicitly requests a prototype image.
