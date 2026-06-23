import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Brain,
  Trash2,
  Plus,
  Search,
  Loader2,
  AlertTriangle,
  FolderOpen
} from "lucide-react";
import {
  useListMemories,
  useCreateMemory,
  useDeleteMemory,
  getListMemoriesQueryKey
} from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { format } from "date-fns";

export default function MemoryPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [searchTerm, setSearchTerm] = useState("");
  const [newContent, setNewContent] = useState("");
  const [newCategory, setNewCategory] = useState("preference");

  const { data: memories, isLoading } = useListMemories();
  const createMemory = useCreateMemory();
  const deleteMemory = useDeleteMemory();

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim()) return;

    createMemory.mutate(
      { data: { content: newContent, category: newCategory } },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getListMemoriesQueryKey() });
          setNewContent("");
          toast({
            title: "Memory created",
            description: "SAGE has updated its database memory bank.",
          });
        },
        onError: (err: any) => {
          toast({
            title: "Failed to create memory",
            description: err.message,
            variant: "destructive",
          });
        },
      }
    );
  };

  const handleDelete = (id: number) => {
    deleteMemory.mutate(
      { id },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({ queryKey: getListMemoriesQueryKey() });
          toast({
            title: "Memory deleted",
            description: "Entry deleted from SAGE's database.",
          });
        },
        onError: (err: any) => {
          toast({
            title: "Deletion failed",
            description: err.message,
            variant: "destructive",
          });
        },
      }
    );
  };

  const filteredMemories = (memories || []).filter((mem) => {
    const matchSearch = mem.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
                        mem.category.toLowerCase().includes(searchTerm.toLowerCase());
    return matchSearch;
  });

  return (
    <div className="h-full flex flex-col p-8 max-w-6xl mx-auto w-full overflow-auto">
      <header className="flex items-center justify-between mb-8 shrink-0">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <Brain className="w-8 h-8 text-primary" />
            Memory Banks
          </h1>
          <p className="text-muted-foreground mt-2 font-mono text-sm">SAGE.NEURAL.MEMORY_CORE</p>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 flex-1 items-start min-h-0">
        {/* Left Side: Creation Form */}
        <Card className="bg-card/40 border-border/50 backdrop-blur-md relative group lg:col-span-1 border-primary/20">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent pointer-events-none" />
          <CardHeader>
            <CardTitle className="font-mono text-sm tracking-widest text-primary flex items-center gap-2">
              <Plus className="w-4 h-4" />
              ADD_NEW_MEMORY
            </CardTitle>
            <CardDescription className="text-xs">
              SAGE automatically learns from chat commands, but you can manually insert preferences and facts here.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <label className="font-mono text-[10px] text-muted-foreground tracking-widest block">CATEGORY</label>
                <Select value={newCategory} onValueChange={setNewCategory}>
                  <SelectTrigger className="bg-background/50 border-border/50">
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent className="bg-background/95 border-border">
                    <SelectItem value="preference">Preference</SelectItem>
                    <SelectItem value="personal">Personal Info</SelectItem>
                    <SelectItem value="work">Work/Projects</SelectItem>
                    <SelectItem value="routine">Routine</SelectItem>
                    <SelectItem value="general">General</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="font-mono text-[10px] text-muted-foreground tracking-widest block">CONTENT</label>
                <Textarea
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  placeholder="e.g. User prefers VS Code for Python development or User starts coding sessions with pnpm run dev."
                  rows={4}
                  className="bg-background/50 border-border/50 resize-none font-mono text-xs focus-visible:ring-primary/40"
                />
              </div>

              <Button
                type="submit"
                disabled={createMemory.isPending || !newContent.trim()}
                className="w-full bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30"
              >
                {createMemory.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Plus className="w-4 h-4 mr-2" />
                )}
                RECORD_FACT
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Right Side: Memory List */}
        <div className="lg:col-span-2 flex flex-col space-y-4 h-full min-h-0">
          {/* Search bar */}
          <div className="relative shrink-0">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search memories by content or category..."
              className="pl-10 bg-card/20 border-border/50 font-mono text-xs"
            />
          </div>

          <div className="flex-1 overflow-y-auto pr-1 space-y-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-primary/50" />
              </div>
            ) : filteredMemories.length === 0 ? (
              <Card className="bg-card/20 border-border/30 p-8 text-center flex flex-col items-center justify-center">
                <FolderOpen className="w-12 h-12 text-muted-foreground/40 mb-3" />
                <div className="text-sm font-mono text-muted-foreground">NO_MEMORIES_FOUND</div>
                <p className="text-xs text-muted-foreground/60 mt-1 max-w-sm">
                  Search query returned no entries, or SAGE hasn't learned anything about you yet.
                </p>
              </Card>
            ) : (
              filteredMemories.map((mem) => (
                <Card
                  key={mem.id}
                  className="bg-card/40 border-border/50 backdrop-blur-sm relative group overflow-hidden hover:border-primary/20 transition-all duration-200"
                >
                  <div className="absolute top-0 left-0 w-1 h-full bg-primary/20 group-hover:bg-primary transition-colors" />
                  <CardHeader className="p-4 pb-2 flex flex-row items-start justify-between space-y-0">
                    <div>
                      <span className="inline-block px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-primary/10 text-primary border border-primary/20">
                        {mem.category}
                      </span>
                      <span className="font-mono text-[9px] text-muted-foreground/60 ml-3">
                        {format(new Date(mem.createdAt), "yyyy-MM-dd HH:mm:ss")}
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(mem.id)}
                      disabled={deleteMemory.isPending}
                      className="w-8 h-8 text-muted-foreground hover:text-destructive shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </CardHeader>
                  <CardContent className="p-4 pt-0">
                    <p className="text-sm text-foreground mt-1 whitespace-pre-wrap leading-relaxed">
                      {mem.content}
                    </p>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
