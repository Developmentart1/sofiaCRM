"use client";

import * as React from "react";
import { useState } from "react";
import { Upload, FileText, Download, AlertCircle, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { contactsApi } from "@/lib/api/contacts";

interface ImportResult {
  created: number;
  updated: number;
  errors: Array<{ row: number; error: string }>;
}

export default function ContactImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await contactsApi.importCsv(file);
      setResult(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al importar");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <Link href="/contacts" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Contactos
      </Link>
      <Card>
        <CardHeader>
          <CardTitle>Importar contactos</CardTitle>
          <CardDescription>Sube un archivo CSV con tus contactos. La primera fila debe ser el encabezado.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md border border-dashed p-6 text-center">
            <input
              id="csv-file"
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="hidden"
            />
            <label htmlFor="csv-file" className="cursor-pointer text-sm">
              <FileText className="mx-auto mb-2 h-8 w-8 text-muted-foreground" aria-hidden="true" />
              {file ? (
                <span className="font-medium">{file.name}</span>
              ) : (
                <span className="text-muted-foreground">Haz clic o arrastra un archivo CSV aquí</span>
              )}
            </label>
          </div>
          <div className="flex items-center justify-between">
            <Button asChild variant="link" size="sm">
              <a href="/sample-contacts.csv" download>
                <Download className="mr-2 h-4 w-4" /> Descargar plantilla
              </a>
            </Button>
            <Button onClick={handleSubmit} disabled={!file || loading}>
              <Upload className="mr-2 h-4 w-4" /> {loading ? "Importando..." : "Importar"}
            </Button>
          </div>
          {error && (
            <div role="alert" className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm">
              <AlertCircle className="mt-0.5 h-4 w-4 text-destructive" />
              <span>{error}</span>
            </div>
          )}
          {result && (
            <div className="space-y-2">
              <div role="status" className="flex items-start gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm">
                <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" />
                <div>
                  <p className="font-medium">Importación completada</p>
                  <p className="text-muted-foreground">
                    {result.created} creados, {result.updated} actualizados, {result.errors.length} errores
                  </p>
                </div>
              </div>
              {result.errors.length > 0 && (
                <div className="max-h-48 overflow-y-auto rounded-md border p-3 text-xs">
                  {result.errors.map((e) => (
                    <div key={e.row} className="border-b py-1 last:border-0">
                      Fila {e.row}: {e.error}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
