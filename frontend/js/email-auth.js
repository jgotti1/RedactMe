import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  sendEmailVerification,
  sendPasswordResetEmail,
  validatePassword,
} from "firebase/auth";

export async function createEmailAccount(auth, email, password) {
  const policy = await validatePassword(auth, password);
  if (!policy.isValid) {
    const requirements = [];
    if (policy.containsLowercaseLetter === false) requirements.push("a lowercase letter");
    if (policy.containsUppercaseLetter === false) requirements.push("an uppercase letter");
    if (policy.containsNumericCharacter === false) requirements.push("a number");
    if (policy.containsNonAlphanumericCharacter === false) requirements.push("a special character");
    if (policy.meetsMinPasswordLength === false) requirements.push(`at least ${policy.passwordPolicy.customStrengthOptions.minPasswordLength} characters`);
    if (policy.meetsMaxPasswordLength === false) requirements.push("a shorter password");
    throw new Error(`Your password needs ${requirements.join(", ") || "to meet this project’s password policy"}.`);
  }
  return createUserWithEmailAndPassword(auth, email, password);
}

export function loginWithEmail(auth, email, password) {
  return signInWithEmailAndPassword(auth, email, password);
}

export function emailVerification(user) {
  return sendEmailVerification(user);
}

export function resetPassword(auth, email) {
  return sendPasswordResetEmail(auth, email);
}

export function authErrorMessage(error) {
  const messages = {
    "auth/invalid-credential": "The email or password is incorrect. Please try again.",
    "auth/user-not-found": "The email or password is incorrect. Please try again.",
    "auth/wrong-password": "The email or password is incorrect. Please try again.",
    "auth/invalid-email": "Enter a valid email address.",
    "auth/email-already-in-use": "Unable to create this account. Try signing in or resetting your password.",
    "auth/weak-password": "Choose a stronger password that meets the project’s password policy.",
    "auth/password-does-not-meet-requirements": "Choose a stronger password that meets the project’s password policy.",
    "auth/too-many-requests": "Too many attempts. Please wait before trying again.",
    "auth/network-request-failed": "Could not connect. Check your internet connection.",
    "auth/operation-not-allowed": "Enable Email/Password sign-in in Firebase Authentication.",
    "auth/user-disabled": "This account is unavailable. Please contact the app owner.",
  };
  return messages[error.code] || (error.code ? "The request could not be completed. Please try again." : error.message);
}
