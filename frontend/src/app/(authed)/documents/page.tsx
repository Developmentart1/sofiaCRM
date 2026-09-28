"use client";

import * as React from "react";
import { useEffect, useRef, useState } from "react";
import { documentsApi } from "@/lib/api/documents";
import type { Document } from "@/lib/types/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatBytes, formatDate } from "@/lib/utils/format";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    setLoading(true);
    try {
      const res = await documentsApi.list();
      setDocs(res.items);
    } catch {
      // toast
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await documentsApi.upload({ file });
      await load();
      if (fileRef.current) fileRef.current.value = "";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al subir el archivo");
    } finally {
      setUploading(false);
    }
  };

  const onDelete = async (id: string) => {
    try {
      await documentsApi.remove(id);
      await load();
    } catch {
      // toast
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Documentos</h1>
          <p className="text-sm text-muted-foreground">Archivos subidos de tu organización.</p>
        </div>
        <div>
          <input
            ref={fileRef}
            type="file"
            onChange={onUpload}
            className="hidden"
            id="document-upload"
          />
          <Button asChild variant="default" disabled={uploading}>
            <label htmlFor="document-upload" className="cursor-pointer">
              {uploading ? "Subiendo..." : "Subir documento"}
            </label>
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {loading ? (
        <div className="p-8 text-muted-foreground">Cargando...</div>
      ) : docs.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center text-muted-foreground">
            No hay documentos todavía.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {docs.map((d) => (
            <Card key={d.id}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{d.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatBytes(d.size)} · {d.folder ?? "Sin carpeta"} · {formatDate(d.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button asChild variant="outline" size="sm">
                    <a href={d.url}>Descargar</a>
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => void onDelete(d.id)}>
                    Eliminar
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
