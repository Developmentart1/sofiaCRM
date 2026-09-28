"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { loginSchema, type LoginInput } from "@/lib/utils/validation";
import { useAuth } from "@/lib/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField } from "@/components/common/form-field";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { APP_NAME } from "@/lib/config";

function getNextUrl(): string {
  if (typeof window === "undefined") return "/dashboard";
  const p = new URLSearchParams(window.location.search);
  return p.get("next") || "/dashboard";
}

export default function LoginPage() {
  const router = useRouter();
  const next = getNextUrl();
  const { login, isAuthenticated, loading: authLoading } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", organization_slug: "" },
  });

  React.useEffect(() => {
    if (!authLoading && isAuthenticated) router.replace(next);
  }, [isAuthenticated, authLoading, router, next]);

  const onSubmit = handleSubmit(async (data) => {
    try {
      await login(data);
      router.replace(next);
    } catch {
      // toast handled in hook
    }
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-1 text-center">
          <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground font-bold">
            C
          </div>
          <CardTitle className="text-xl">Iniciar sesión</CardTitle>
          <CardDescription>Accede a {APP_NAME}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-3" noValidate>
            <FormField label="Slug de la organización" htmlFor="organization_slug" error={errors.organization_slug?.message} required>
              <Input id="organization_slug" type="text" placeholder="ej: crm-splash-demo" autoComplete="organization" aria-invalid={!!errors.organization_slug} {...register("organization_slug")} />
            </FormField>
            <FormField label="Email" htmlFor="email" error={errors.email?.message} required>
              <Input id="email" type="email" autoComplete="email" aria-invalid={!!errors.email} {...register("email")} />
            </FormField>
            <FormField label="Contraseña" htmlFor="password" error={errors.password?.message} required>
              <Input id="password" type="password" autoComplete="current-password" aria-invalid={!!errors.password} {...register("password")} />
            </FormField>
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Ingresando..." : "Ingresar"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            ¿No tienes cuenta?{" "}
            <Link href="/signup" className="font-medium text-primary hover:underline">Crear cuenta</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
