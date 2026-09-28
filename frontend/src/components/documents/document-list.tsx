"use client";

import { FileText } from "lucide-react";

interface DocumentListProps {
  contactId?: string;
  documents?: unknown[];
  onChange?: () => Promise<void>;
}

export function DocumentList({ contactId: _cid, documents: _docs, onChange: _onChange }: DocumentListProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
      <FileText className="h-12 w-12 mb-4" />
      <p className="text-sm">No hay documentos aún</p>
    </div>
  );
}
