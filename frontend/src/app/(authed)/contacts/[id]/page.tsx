"use client";

import * as React from "react";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Mail,
  Phone,
  Briefcase,
  Building2,
  Tag,
  Edit,
  Trash2,
  Plus,
  FileText,
  Activity as ActivityIcon,
  ListTodo,
  Target,
  Settings,
  History,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { LoadingPage, Skeleton } from "@/components/common/loading-spinner";
import { ErrorState } from "@/components/common/error-state";
import { ContactForm } from "@/components/contacts/contact-form";
import { ActivityFeed } from "@/components/activities/activity-feed";
import { ActivityForm } from "@/components/activities/activity-form";
import { TaskList } from "@/components/tasks/task-list";
import { DocumentList } from "@/components/documents/document-list";
import {
  useContact,
  useContactActivities,
  useContactAudit,
  useContactDocuments,
  useContactOpportunities,
  useContactTasks,
  useCompanies,
} from "@/lib/hooks/use-contacts";
import { activitiesApi } from "@/lib/api/activities";
import { contactsApi } from "@/lib/api/contacts";
import { formatDate, formatRelative, fullName, initials } from "@/lib/utils/format";
import type { ActivityInput } from "@/lib/utils/validation";
import { useDebounce } from "@/lib/hooks/use-debounce";

export default function ContactDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params?.id;
  const { contact, loading, error, refresh, setContact } = useContact(id);
  const { items: activities, refresh: refreshActivities } = useContactActivities(id);
  const { items: tasks } = useContactTasks(id);
  const { items: opportunities } = useContactOpportunities(id);
  const { items: documents, refresh: refreshDocs } = useContactDocuments(id);
  const { items: audit } = useContactAudit(id);

  const [editOpen, setEditOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [companySearch, setCompanySearch] = useState("");
  const debounced = useDebounce(companySearch, 300);
  const { items: companies } = useCompanies({ search: debounced || undefined, page: 1, page_size: 50 });

  if (loading) return <LoadingPage />;
  if (error || !contact) return <ErrorState message={error ?? "Contacto no encontrado"} onRetry={refresh} />;

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await contactsApi.remove(contact.id);
      router.push("/contacts");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Link href="/contacts" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Contactos
        </Link>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-start gap-4 p-4">
          <Avatar className="h-14 w-14">
            <AvatarFallback className="text-base">{initials(contact.first_name, contact.last_name)}</AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-semibold">{fullName(contact.first_name, contact.last_name)}</h1>
              <Badge variant={contact.status === "customer" ? "default" : contact.status === "active" ? "success" : "secondary"}>
                {contact.status}
              </Badge>
              {contact.source && <Badge variant="outline">{contact.source}</Badge>}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
              {contact.job_title && <span className="inline-flex items-center gap-1"><Briefcase className="h-3.5 w-3.5" /> {contact.job_title}</span>}
              {contact.company_id && contact.company_name && (
                <Link href={`/companies/${contact.company_id}`} className="inline-flex items-center gap-1 hover:text-foreground">
                  <Building2 className="h-3.5 w-3.5" /> {contact.company_name}
                </Link>
              )}
              {contact.email && (
                <a href={`mailto:${contact.email}`} className="inline-flex items-center gap-1 hover:text-foreground">
                  <Mail className="h-3.5 w-3.5" /> {contact.email}
                </a>
              )}
              {contact.phone && (
                <a href={`tel:${contact.phone}`} className="inline-flex items-center gap-1 hover:text-foreground">
                  <Phone className="h-3.5 w-3.5" /> {contact.phone}
                </a>
              )}
            </div>
            {contact.tags.length > 0 && (
              <div className="mt-2 flex flex-wrap items-center gap-1">
                <Tag className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                {contact.tags.map((t) => (
                  <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>
                ))}
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => setActivityOpen(true)}>
              <Plus className="mr-2 h-4 w-4" /> Actividad
            </Button>
            <Button size="sm" variant="outline" onClick={() => setEditOpen(true)}>
              <Edit className="mr-2 h-4 w-4" /> Editar
            </Button>
            <Button size="sm" variant="destructive" onClick={() => setConfirmDelete(true)}>
              <Trash2 className="mr-2 h-4 w-4" /> Eliminar
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="overview">
        <TabsList className="flex-wrap">
          <TabsTrigger value="overview">Resumen</TabsTrigger>
          <TabsTrigger value="opportunities">Oportunidades</TabsTrigger>
          <TabsTrigger value="activity">Actividad</TabsTrigger>
          <TabsTrigger value="tasks">Tareas</TabsTrigger>
          <TabsTrigger value="notes">Notas</TabsTrigger>
          <TabsTrigger value="documents">Documentos</TabsTrigger>
          <TabsTrigger value="custom">Custom</TabsTrigger>
          <TabsTrigger value="audit">Auditoría</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-3">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Información</CardTitle></CardHeader>
              <CardContent className="space-y-1.5 text-sm">
                <div className="flex justify-between"><span className="text-muted-foreground">Creado</span><span>{formatDate(contact.created_at)}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Actualizado</span><span>{formatRelative(contact.updated_at)}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Propietario</span><span>{contact.owner_name ?? "—"}</span></div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Actividad reciente</CardTitle></CardHeader>
              <CardContent>
                <p className="text-sm">{activities.length} actividades registradas</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Tareas abiertas</CardTitle></CardHeader>
              <CardContent>
                <p className="text-sm">{tasks.filter((t) => t.status !== "completed").length} tareas pendientes</p>
              </CardContent>
            </Card>
          </div>
          {contact.notes && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Notas</CardTitle></CardHeader>
              <CardContent><p className="whitespace-pre-wrap text-sm">{contact.notes}</p></CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="opportunities">
          {opportunities.length === 0 ? (
            <Card><CardContent className="py-6 text-center text-sm text-muted-foreground">Sin oportunidades asociadas</CardContent></Card>
          ) : (
            <ul className="space-y-2">
              {opportunities.map((o) => (
                <li key={o.id}>
                  <Link href={`/opportunities/${o.id}`} className="block">
                    <Card className="hover:border-primary/30">
                      <CardContent className="flex items-center justify-between gap-2 p-3">
                        <div>
                          <p className="text-sm font-medium">{o.name}</p>
                          <p className="text-xs text-muted-foreground">{'Etapa'} · {'Pipeline'}</p>
                        </div>
                        <Badge variant={o.status === "won" ? "success" : o.status === "lost" ? "destructive" : "secondary"}>
                          {o.status}
                        </Badge>
                      </CardContent>
                    </Card>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>

        <TabsContent value="activity">
          <ActivityFeed
            activities={activities}
            onDelete={async (aid) => {
              await activitiesApi.remove(aid);
              await refreshActivities();
            }}
          />
        </TabsContent>

        <TabsContent value="tasks">
          <TaskList contactId={contact.id} />
        </TabsContent>

        <TabsContent value="notes">
          <Card>
            <CardContent className="p-4">
              {contact.notes ? (
                <p className="whitespace-pre-wrap text-sm">{contact.notes}</p>
              ) : (
                <p className="text-sm text-muted-foreground">Sin notas. Edita el contacto para añadir.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="documents">
          <DocumentList
            contactId={contact.id}
            documents={documents}
            onChange={refreshDocs}
          />
        </TabsContent>

        <TabsContent value="custom">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Settings className="h-4 w-4" /> Campos personalizados
              </CardTitle>
            </CardHeader>
            <CardContent>
              {Object.keys(contact.custom_fields).length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin campos personalizados</p>
              ) : (
                <dl className="space-y-1.5 text-sm">
                  {Object.entries(contact.custom_fields).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <dt className="text-muted-foreground">{k}</dt>
                      <dd>{String(v ?? "—")}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="audit">
          <Card>
            <CardHeader className="pb-2"><CardTitle className="flex items-center gap-2 text-sm"><History className="h-4 w-4" /> Historial</CardTitle></CardHeader>
            <CardContent>
              {audit.length === 0 ? (
                <p className="text-sm text-muted-foreground">Sin cambios registrados</p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {audit.map((a) => (
                    <li key={a.id} className="flex items-start gap-2">
                      <ActivityIcon className="mt-0.5 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                      <div>
                        <p>{a.user_name} <span className="text-muted-foreground">· {a.action}</span></p>
                        <p className="text-xs text-muted-foreground">{formatDateTime(a.created_at)}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>Editar contacto</DialogTitle></DialogHeader>
          <ContactForm
            defaultValues={contact}
            companies={companies}
            submitLabel="Guardar cambios"
            onSubmit={async (data) => {
              const updated = await contactsApi.update(contact.id, {
                ...data,
                company_id: data.company_id || null,
                email: data.email || null,
                phone: data.phone || null,
                job_title: data.job_title || null,
                source: data.source || null,
                notes: data.notes || null,
              });
              setContact(updated);
              setEditOpen(false);
              await refresh();
            }}
          />
        </DialogContent>
      </Dialog>

      <Dialog open={activityOpen} onOpenChange={setActivityOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Registrar actividad</DialogTitle></DialogHeader>
          <ActivityForm
            defaultValues={{ contact_id: contact.id }}
            onSubmit={async (data: ActivityInput) => {
              await activitiesApi.create({ ...data, contact_id: contact.id });
              setActivityOpen(false);
              await refreshActivities();
            }}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Eliminar contacto"
        description={`¿Seguro que quieres eliminar a ${fullName(contact.first_name, contact.last_name)}?`}
        destructive
        loading={deleting}
        onConfirm={handleDelete}
      />
    </div>
  );
}

function formatDateTime(d: string): string {
  return formatDate(d) + " " + d.slice(11, 16);
}
