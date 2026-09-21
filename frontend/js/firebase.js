import { initializeApp } from "firebase/app";
import { initializeAuth, inMemoryPersistence, browserPopupRedirectResolver, GoogleAuthProvider } from "firebase/auth";

const config = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};
if (Object.values(config).some((value) => !value)) {
  throw new Error("Firebase frontend configuration is missing. Check frontend/.env.");
}
// In-memory persistence: the sign-in lives only in this page, so refreshing or closing the tab signs the user out.
export const auth = initializeAuth(initializeApp(config), {
  persistence: inMemoryPersistence,
  popupRedirectResolver: browserPopupRedirectResolver,
});
export const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: "select_account" });
