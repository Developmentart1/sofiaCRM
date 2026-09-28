"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { signupSchema, type SignupInput } from "@/lib/utils/validation";
import { useAuth } from "@/lib/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FormField } from "@/components/common/form-field";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SignupPage() {
  const router = useRouter();
  const { signup, isAuthenticated, loading: authLoading } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupInput>({
    resolver: zodResolver(signupSchema),
    defaultValues: { organization_name: "", full_name: "", email: "", password: "" },
  });

  React.useEffect(() => {
    if (!authLoading && isAuthenticated) router.replace("/dashboard");
  }, [isAuthenticated, authLoading, router]);

  const onSubmit = handleSubmit(async (data) => {
    try {
      await signup(data);
      router.replace("/dashboard");
    } catch {
      // toast handled in hook
    }
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground font-bold">
            C
          </div>
          <CardTitle className="text-xl">Crear tu cuenta</CardTitle>
          <CardDescription>Crea tu organización y empieza a vender</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-3" noValidate>
            <FormField label="Organización" htmlFor="organization_name" error={errors.organization_name?.message} required>
              <Input id="organization_name" aria-invalid={!!errors.organization_name} {...register("organization_name")} />
            </FormField>
            <FormField label="Tu nombre" htmlFor="full_name" error={errors.full_name?.message} required>
              <Input id="full_name" autoComplete="name" aria-invalid={!!errors.full_name} {...register("full_name")} />
            </FormField>
            <FormField label="Email" htmlFor="email" error={errors.email?.message} required>
              <Input id="email" type="email" autoComplete="email" aria-invalid={!!errors.email} {...register("email")} />
            </FormField>
            <FormField label="Contraseña" htmlFor="password" error={errors.password?.message} description="Mínimo 8 caracteres" required>
              <Input id="password" type="password" autoComplete="new-password" aria-invalid={!!errors.password} {...register("password")} />
            </FormField>
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Creando..." : "Crear cuenta"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            ¿Ya tienes cuenta?{" "}
            <Link href="/login" className="font-medium text-primary hover:underline">
              Iniciar sesión
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
