import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import {
  CheckSquare,
  Plus,
  Trash2,
  Clock,
  AlertCircle,
  Loader2,
  CheckCircle2,
  Circle
} from "lucide-react";
import {
  useListTodos,
  useCreateTodo,
  useUpdateTodo,
  useDeleteTodo,
  getListTodosQueryKey
} from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

export default function TodosPage() {
  const { data: todos, isLoading } = useListTodos();
  const [newTitle, setNewTitle] = useState("");
  const [newPriority, setNewPriority] = useState("medium");
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const createTodo = useCreateTodo();
  const updateTodo = useUpdateTodo();
  const deleteTodo = useDeleteTodo();

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    createTodo.mutate({ data: { title: newTitle, priority: newPriority } }, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListTodosQueryKey() });
        setNewTitle("");
        setNewPriority("medium");
      }
    });
  };

  const handleToggle = (id: number, completed: boolean) => {
    updateTodo.mutate({ id, data: { completed: !completed } }, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListTodosQueryKey() });
      }
    });
  };

  const handleDelete = (id: number) => {
    deleteTodo.mutate({ id }, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListTodosQueryKey() });
      }
    });
  };

  const priorityColors: Record<string, string> = {
    low: "text-blue-400 border-blue-400/20 bg-blue-400/10",
    medium: "text-yellow-400 border-yellow-400/20 bg-yellow-400/10",
    high: "text-destructive border-destructive/20 bg-destructive/10"
  };

  return (
    <div className="h-full flex flex-col p-8 max-w-4xl mx-auto w-full">
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <CheckSquare className="w-8 h-8 text-primary" />
            Task Directives
          </h1>
          <p className="text-muted-foreground mt-2 font-mono text-sm">SYSTEM.TASKS.QUEUE</p>
        </div>
      </header>

      <Card className="mb-8 bg-card/40 border-border/50 backdrop-blur-md">
        <CardContent className="p-4">
          <form onSubmit={handleCreate} className="flex gap-4">
            <Input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="Enter new directive..."
              className="flex-1 bg-background/50 border-border/50 h-12"
            />
            <Select value={newPriority} onValueChange={setNewPriority}>
              <SelectTrigger className="w-36 h-12 bg-background/50">
                <SelectValue placeholder="Priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Low Priority</SelectItem>
                <SelectItem value="medium">Medium Priority</SelectItem>
                <SelectItem value="high">High Priority</SelectItem>
              </SelectContent>
            </Select>
            <Button type="submit" disabled={createTodo.isPending || !newTitle.trim()} className="h-12 w-12 p-0 shrink-0">
              {createTodo.isPending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="flex-1 overflow-auto pr-2 space-y-3">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : todos?.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center text-muted-foreground border border-dashed border-border/50 rounded-xl bg-card/10">
            <AlertCircle className="w-12 h-12 mb-4 opacity-50" />
            <p className="font-mono text-sm">NO_DIRECTIVES_IN_QUEUE</p>
          </div>
        ) : (
          todos?.sort((a, b) => {
            if (a.completed !== b.completed) return a.completed ? 1 : -1;
            const p: Record<string, number> = { high: 3, medium: 2, low: 1 };
            return p[b.priority] - p[a.priority];
          }).map((todo) => (
            <div
              key={todo.id}
              className={cn(
                "group flex items-center gap-4 p-4 rounded-xl border transition-all duration-300",
                todo.completed 
                  ? "bg-muted/30 border-border/30 opacity-60 grayscale" 
                  : "bg-card/50 border-border/50 hover:border-primary/30 shadow-sm"
              )}
            >
              <button
                onClick={() => handleToggle(todo.id, todo.completed)}
                className="shrink-0 text-muted-foreground hover:text-primary transition-colors"
              >
                {todo.completed ? (
                  <CheckCircle2 className="w-6 h-6 text-primary" />
                ) : (
                  <Circle className="w-6 h-6" />
                )}
              </button>
              
              <div className="flex-1 overflow-hidden">
                <h3 className={cn(
                  "font-medium truncate transition-all",
                  todo.completed ? "line-through text-muted-foreground" : "text-foreground"
                )}>
                  {todo.title}
                </h3>
                <div className="flex items-center gap-3 mt-1 font-mono text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {format(new Date(todo.createdAt), "MMM d, HH:mm")}
                  </span>
                  <span className={cn(
                    "px-2 py-0.5 rounded-full border text-[10px] tracking-wider uppercase",
                    priorityColors[todo.priority]
                  )}>
                    {todo.priority}
                  </span>
                </div>
              </div>

              <Button
                variant="ghost"
                size="icon"
                className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-opacity"
                onClick={() => handleDelete(todo.id)}
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
