import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "wouter";
import { format } from "date-fns";
import {
  StickyNote,
  Plus,
  Trash2,
  Edit2,
  FileText,
  Search,
  X,
  Loader2
} from "lucide-react";
import {
  useListNotes,
  useCreateNote,
  useUpdateNote,
  useDeleteNote,
  getListNotesQueryKey
} from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

export default function NotesPage() {
  const { data: notes, isLoading } = useListNotes();
  const [search, setSearch] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [currentNote, setCurrentNote] = useState<{ id: number; title: string; content: string } | null>(null);

  const queryClient = useQueryClient();
  const { toast } = useToast();

  const createNote = useCreateNote();
  const updateNote = useUpdateNote();
  const deleteNote = useDeleteNote();

  const filteredNotes = notes?.filter(note =>
    note.title.toLowerCase().includes(search.toLowerCase()) ||
    note.content.toLowerCase().includes(search.toLowerCase())
  ) || [];

  const handleCreate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const title = formData.get("title") as string;
    const content = formData.get("content") as string;

    createNote.mutate({ data: { title, content } }, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListNotesQueryKey() });
        setIsCreateOpen(false);
        toast({ title: "Note created successfully" });
      }
    });
  };

  const handleEdit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!currentNote) return;
    const formData = new FormData(e.currentTarget);
    const title = formData.get("title") as string;
    const content = formData.get("content") as string;

    updateNote.mutate({ id: currentNote.id, data: { title, content } }, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListNotesQueryKey() });
        setIsEditOpen(false);
        toast({ title: "Note updated successfully" });
      }
    });
  };

  const handleDelete = (id: number) => {
    deleteNote.mutate({ id }, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListNotesQueryKey() });
        toast({ title: "Note deleted successfully" });
      }
    });
  };

  return (
    <div className="h-full flex flex-col p-8 max-w-6xl mx-auto w-full">
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <StickyNote className="w-8 h-8 text-primary" />
            Knowledge Base
          </h1>
          <p className="text-muted-foreground mt-2 font-mono text-sm">SYSTEM.NOTES.REGISTRY</p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} className="gap-2 border-primary/50 hover:bg-primary/20">
          <Plus className="w-4 h-4" />
          New Entry
        </Button>
      </header>

      <div className="mb-6 relative group">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-muted-foreground group-focus-within:text-primary transition-colors" />
        </div>
        <Input
          placeholder="Search entries..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10 bg-card/50 border-border/50 focus-visible:border-primary/50 h-12"
        />
        {search && (
          <button
            onClick={() => setSearch("")}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-auto pb-8">
        {isLoading ? (
          <div className="flex items-center justify-center h-40">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : filteredNotes.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center text-muted-foreground border border-dashed border-border/50 rounded-xl bg-card/10">
            <FileText className="w-12 h-12 mb-4 opacity-50" />
            <p className="font-mono text-sm">NO_ENTRIES_FOUND</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredNotes.map((note) => (
              <Card key={note.id} className="bg-card/40 border-border/40 backdrop-blur-sm hover:border-primary/30 transition-colors group">
                <CardContent className="p-5 flex flex-col h-[200px]">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-semibold text-lg line-clamp-1 group-hover:text-primary transition-colors">
                      {note.title}
                    </h3>
                    <div className="flex opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-foreground"
                        onClick={() => {
                          setCurrentNote(note);
                          setIsEditOpen(true);
                        }}
                      >
                        <Edit2 className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        onClick={() => handleDelete(note.id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                  <p className="text-muted-foreground text-sm flex-1 overflow-hidden overflow-ellipsis whitespace-pre-wrap">
                    {note.content}
                  </p>
                  <div className="mt-4 pt-4 border-t border-border/30 text-xs font-mono text-muted-foreground opacity-70">
                    UPDATED: {format(new Date(note.updatedAt), "yyyy-MM-dd HH:mm:ss")}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="bg-card/95 backdrop-blur-xl border-border/50">
          <DialogHeader>
            <DialogTitle className="font-mono text-primary">NEW_ENTRY.CREATE</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Title</Label>
              <Input id="title" name="title" required className="bg-background/50" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="content">Content</Label>
              <Textarea id="content" name="content" required className="min-h-[200px] bg-background/50 font-mono text-sm" />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={createNote.isPending}>
                {createNote.isPending ? "Creating..." : "Save Entry"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="bg-card/95 backdrop-blur-xl border-border/50">
          <DialogHeader>
            <DialogTitle className="font-mono text-primary">ENTRY.UPDATE</DialogTitle>
          </DialogHeader>
          {currentNote && (
            <form onSubmit={handleEdit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="edit-title">Title</Label>
                <Input id="edit-title" name="title" defaultValue={currentNote.title} required className="bg-background/50" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-content">Content</Label>
                <Textarea id="edit-content" name="content" defaultValue={currentNote.content} required className="min-h-[200px] bg-background/50 font-mono text-sm" />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsEditOpen(false)}>Cancel</Button>
                <Button type="submit" disabled={updateNote.isPending}>
                  {updateNote.isPending ? "Saving..." : "Update Entry"}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
