# tigrify-server-impl

Cloud Functions backend (`api`) for Firebase project `tigrify-515619`.
Firebase Hosting and Firestore rules remain in `tigrify-deploy`.

## Deploy Functions Only
```powershell
npx -y firebase-tools@latest deploy --only functions:default --project tigrify-515619
```

## Run Tests
```powershell
.\functions\venv\Scripts\python.exe -m unittest discover -s functions\tests -v
```

## Preventing Client/API Drift
1. `functions/openapi.snapshot.json` snapshots `create_app().openapi()`.
2. `functions/tests/test_openapi_contract.py` verifies all client-consumed routes match the snapshot.
3. For breaking schema changes, follow **Expand -> Migrate Client (`tigrify-deploy`) -> Contract**.
4. Set `FIREBASE_WEB_API_KEY` in Cloud Functions env config to avoid depending on Hosting `__/firebase/init.json`.
