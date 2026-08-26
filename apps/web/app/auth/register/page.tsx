import { AuthForm } from "@/components/auth/AuthForm";

export const metadata = {
  title: "Create account | CVMatcher",
};

export default function RegisterPage() {
  return <AuthForm mode="register" />;
}
