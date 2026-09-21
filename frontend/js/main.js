import { onAuthStateChanged, signInWithPopup, signOut } from "firebase/auth";
import { createEmailAccount, loginWithEmail, emailVerification, resetPassword, authErrorMessage } from "./email-auth.js";
import { showWorkspace } from "./workspace.js";

const loginButton = document.querySelector("#google-login");
const logoutButton = document.querySelector("#logout");
const status = document.querySelector("#status");
const emailForm = document.querySelector("#email-form");
const emailInput = document.querySelector("#email");
const passwordInput = document.querySelector("#password");
const confirmInput = document.querySelector("#confirm-password");
const emailSubmit = document.querySelector("#email-submit");
const switchMode = document.querySelector("#switch-mode");
const forgotPassword = document.querySelector("#forgot-password");
const verificationPanel = document.querySelector("#verification-panel");
const verificationStatus = document.querySelector("#verification-status");
let mode = "login";
let auth;
let provider;

function setStatus(message, error = false) {
  const target = auth?.currentUser ? document.querySelector("#workspace-status") : status;
  target.textContent = message;
  target.classList.toggle("error", error);
}

loginButton.disabled = true;
async function initializeAuth() {
try {
  const firebase = await import("./firebase.js");
  auth = firebase.auth;
  provider = firebase.googleProvider;
  onAuthStateChanged(auth, (user) => {
    document.querySelector("#login-page").hidden = Boolean(user);
    document.querySelector("#workspace").hidden = !user;
    document.querySelector("#header-account").hidden = !user;
    document.querySelector("#header-badge").hidden = Boolean(user);
    history.replaceState(null, "", user ? "/app" : "/");
    document.title = user ? "Workspace | Redact Me" : "Sign in | Redact Me";
    verificationPanel.hidden = !user || user.emailVerified || !user.providerData.some((provider) => provider.providerId === "password");
    if (user) {
      showWorkspace(user);
      document.querySelector("#account").textContent = user.displayName || user.email || "Your account";
      document.querySelector("#workspace-title").focus();
    } else {
      document.querySelector("#account").textContent = "";
      setStatus("Sign in with Google or your email address.");
      setAuthBusy(false);
    }
  });
} catch {
  setStatus("Firebase configuration could not be loaded. Check frontend/.env and restart the frontend.", true);
}

}
initializeAuth();

loginButton.addEventListener("click", async () => {
  setAuthBusy(true);
  setStatus("Complete sign-in in the Google window.");
  try {
    await signInWithPopup(auth, provider);
  } catch (error) {
    const messages = {
      "auth/popup-closed-by-user": "Sign-in was cancelled. You can try again.",
      "auth/popup-blocked": "Allow popups for this site, then try again.",
      "auth/unauthorized-domain": "Add this hostname to Firebase Authentication’s authorized domains.",
      "auth/operation-not-allowed": "Enable Google sign-in in Firebase Authentication.",
      "auth/network-request-failed": "Sign-in could not connect. Check your internet connection.",
      "auth/invalid-api-key": "The Firebase web API key is invalid. Check frontend/.env.",
    };
    setStatus(messages[error.code] || "Google sign-in failed. Please try again.", true);
  } finally {
    setAuthBusy(false);
  }
});
logoutButton.addEventListener("click", async () => {
  logoutButton.disabled = true;
  try { await signOut(auth); }
  catch { setStatus("Sign-out failed. Please try again.", true); }
  finally { logoutButton.disabled = false; }
});


function setAuthBusy(busy) {
  for (const control of [loginButton, emailSubmit, switchMode, forgotPassword]) {
    control.disabled = busy || !auth;
  }
  emailForm.setAttribute("aria-busy", String(busy));
}

function setMode(next) {
  mode = next;
  const signup = mode === "signup";
  const reset = mode === "reset";
  document.querySelector("#password-field").hidden = reset;
  passwordInput.disabled = reset;
  passwordInput.required = !reset;
  passwordInput.minLength = signup ? 6 : 1;
  passwordInput.autocomplete = signup ? "new-password" : "current-password";
  passwordInput.value = "";
  confirmInput.value = "";
  confirmInput.setCustomValidity("");
  confirmInput.disabled = !signup;
  confirmInput.required = signup;
  document.querySelector("#confirm-field").hidden = !signup;
  document.querySelector("#password-help").hidden = !signup;
  emailSubmit.textContent = signup ? "Create account" : reset ? "Send password reset" : "Sign in with email";
  document.querySelector("#switch-prompt").textContent = signup ? "Already have an account?" : reset ? "Remember your password?" : "New to Redact Me?";
  switchMode.textContent = signup || reset ? "Back to sign in" : "Create an account";
  document.querySelector("#welcome").textContent = signup ? "Create your account" : reset ? "Reset your password" : "Welcome to Redact Me";
  document.querySelector("#card-subtitle").textContent = signup ? "Start with an email address and password." : reset ? "We’ll help you get back to your workspace." : "Sign in to get started with your workspace.";
  setStatus(reset ? "Enter your account email to request a reset link." : signup ? "Firebase securely manages your account credentials." : "Sign in with Google or your email address.");
}

switchMode.addEventListener("click", () => setMode(mode === "login" ? "signup" : "login"));
forgotPassword.addEventListener("click", () => setMode("reset"));
for (const input of [passwordInput, confirmInput]) {
  input.addEventListener("input", () => confirmInput.setCustomValidity(""));
}

emailForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!auth || emailSubmit.disabled) return;
  if (mode === "signup" && passwordInput.value !== confirmInput.value) {
    confirmInput.setCustomValidity("Passwords must match.");
    confirmInput.reportValidity();
    return;
  }
  if (!emailForm.reportValidity()) return;
  const email = emailInput.value.trim();
  setAuthBusy(true);
  setStatus(mode === "signup" ? "Creating your account…" : mode === "reset" ? "Requesting a reset link…" : "Signing in…");
  try {
    if (mode === "reset") {
      await resetPassword(auth, email);
      setStatus("If this email has an account, you’ll receive a password reset link. Check your inbox and spam folder.");
    } else if (mode === "signup") {
      const credential = await createEmailAccount(auth, email, passwordInput.value);
      emailForm.reset();
      try {
        await emailVerification(credential.user);
        verificationStatus.textContent = "Verification email sent. Check your inbox and spam folder, then open the link.";
      } catch {
        verificationStatus.textContent = "Your account was created, but the verification email could not be sent. Use the button below to try again.";
      }
    } else {
      await loginWithEmail(auth, email, passwordInput.value);
      emailForm.reset();
    }
  } catch (error) {
    // Reset responses do not reveal whether an email address is registered.
    if (mode === "reset" && error.code === "auth/user-not-found") {
      setStatus("If this email has an account, you’ll receive a password reset link. Check your inbox and spam folder.");
    } else {
      setStatus(authErrorMessage(error), true);
    }
    passwordInput.value = "";
    confirmInput.value = "";
  } finally {
    setAuthBusy(false);
  }
});

document.querySelector("#resend-verification").addEventListener("click", async (event) => {
  const user = auth?.currentUser;
  if (!user) return;
  const button = event.currentTarget;
  button.disabled = true;
  try {
    await emailVerification(user);
    verificationStatus.textContent = "Verification email sent. Check your inbox and spam folder.";
  } catch (error) {
    verificationStatus.textContent = authErrorMessage(error);
  } finally { button.disabled = false; }
});
document.querySelector("#check-verification").addEventListener("click", async (event) => {
  const user = auth?.currentUser;
  if (!user) return;
  const button = event.currentTarget;
  button.disabled = true;
  try {
    await user.reload();
    if (auth.currentUser?.uid !== user.uid) return;
    if (user.emailVerified) {
      await user.getIdToken(true);
      verificationPanel.hidden = true;
      setStatus("Your email is verified.");
    } else {
      verificationStatus.textContent = "Your email is not verified yet. Open the link in your email, then check again.";
    }
  } catch {
    verificationStatus.textContent = "Could not check verification. Try again.";
  } finally { button.disabled = false; }
});
setAuthBusy(true);

window.addEventListener("popstate", () => {
  if (auth) history.replaceState(null, "", auth.currentUser ? "/app" : "/");
});
