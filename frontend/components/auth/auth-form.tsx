"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const authSchema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(8, "Password must be at least 8 characters."),
});

type AuthFormValues = z.infer<typeof authSchema>;

type AuthFormProps = {
  mode: "login" | "register";
};

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, register } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);
  const isRegister = mode === "register";
  const nextParam = searchParams.get("next");
  const nextPath = nextParam?.startsWith("/") ? nextParam : "/app";

  const form = useForm<AuthFormValues>({
    resolver: zodResolver(authSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  async function onSubmit(values: AuthFormValues) {
    setServerError(null);

    try {
      if (isRegister) {
        await register(values);
        toast.success("Account created");
      } else {
        await login(values);
        toast.success("Signed in");
      }

      router.replace(nextPath);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Authentication failed.";
      setServerError(message);
    }
  }

  return (
    <Card className="w-full max-w-md rounded-md border border-border shadow-sm">
      <CardHeader>
        <CardTitle className="text-xl">
          {isRegister ? "Create your account" : "Sign in"}
        </CardTitle>
        <CardDescription>
          {isRegister
            ? "Start a local ResearchHub session with your email and password."
            : "Use your ResearchHub credentials to return to the workspace."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              aria-invalid={Boolean(form.formState.errors.email)}
              placeholder="you@example.com"
              {...form.register("email")}
            />
            {form.formState.errors.email ? (
              <p className="text-xs text-destructive">
                {form.formState.errors.email.message}
              </p>
            ) : null}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
              aria-invalid={Boolean(form.formState.errors.password)}
              placeholder="At least 8 characters"
              {...form.register("password")}
            />
            {form.formState.errors.password ? (
              <p className="text-xs text-destructive">
                {form.formState.errors.password.message}
              </p>
            ) : null}
          </div>

          {serverError ? (
            <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {serverError}
            </div>
          ) : null}

          <Button
            type="submit"
            className="h-9 w-full"
            disabled={form.formState.isSubmitting}
          >
            {form.formState.isSubmitting ? (
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              <>
                {isRegister ? "Create account" : "Sign in"}
                <ArrowRight className="size-4" aria-hidden="true" />
              </>
            )}
          </Button>
        </form>

        <div className="mt-5 text-sm text-muted-foreground">
          {isRegister ? "Already have an account?" : "Need an account?"}{" "}
          <Link
            className="font-medium text-primary hover:underline"
            href={isRegister ? "/login" : "/register"}
          >
            {isRegister ? "Sign in" : "Create one"}
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
