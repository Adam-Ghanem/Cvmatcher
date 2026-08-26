import { AuthForm } from "@/components/auth/AuthForm";

export const metadata = {
  title: "Sign in | CVMatcher",
};

export default function LoginPage() {
  return <AuthForm mode="login" />;
}
