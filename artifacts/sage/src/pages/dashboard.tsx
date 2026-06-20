import { useQuery } from "@tanstack/react-query";
import {
  BarChart2,
  MessageSquare,
  StickyNote,
  CheckSquare,
  Activity,
  Terminal,
  Loader2
} from "lucide-react";
import { useGetStats } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

export default function DashboardPage() {
  const { data: stats, isLoading } = useGetStats();

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-12 h-12 animate-spin text-primary" />
      </div>
    );
  }

  const todoProgress = stats?.totalTodos ? (stats.completedTodos / stats.totalTodos) * 100 : 0;

  return (
    <div className="h-full flex flex-col p-8 max-w-6xl mx-auto w-full overflow-auto">
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <BarChart2 className="w-8 h-8 text-primary" />
            System Status
          </h1>
          <p className="text-muted-foreground mt-2 font-mono text-sm">SAGE.TELEMETRY.DASHBOARD</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-primary/10 border border-primary/20 rounded-full text-primary font-mono text-sm shadow-[0_0_15px_rgba(0,255,255,0.1)]">
          <Activity className="w-4 h-4 animate-pulse" />
          SYSTEM_OPTIMAL
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard
          title="SESSIONS"
          value={stats?.totalConversations || 0}
          icon={Terminal}
          description="Active AI dialogues"
        />
        <MetricCard
          title="MESSAGES"
          value={stats?.totalMessages || 0}
          icon={MessageSquare}
          description="Total data exchanged"
        />
        <MetricCard
          title="ENTRIES"
          value={stats?.totalNotes || 0}
          icon={StickyNote}
          description="Knowledge base nodes"
        />
        <MetricCard
          title="DIRECTIVES"
          value={stats?.totalTodos || 0}
          icon={CheckSquare}
          description="Task queue items"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-card/40 border-border/50 backdrop-blur-md overflow-hidden relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent pointer-events-none" />
          <CardHeader>
            <CardTitle className="font-mono text-sm tracking-widest text-primary flex items-center gap-2">
              <Activity className="w-4 h-4" />
              TASK_EXECUTION_RATE
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mt-4 space-y-6">
              <div>
                <div className="flex justify-between font-mono text-sm mb-2 text-muted-foreground">
                  <span>COMPLETION</span>
                  <span className="text-primary">{todoProgress.toFixed(1)}%</span>
                </div>
                <Progress value={todoProgress} className="h-2 bg-muted" />
              </div>
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border/30">
                <div>
                  <div className="text-4xl font-light text-foreground">{stats?.completedTodos || 0}</div>
                  <div className="font-mono text-xs text-muted-foreground mt-1">RESOLVED</div>
                </div>
                <div>
                  <div className="text-4xl font-light text-foreground">{stats?.totalTodos || 0}</div>
                  <div className="font-mono text-xs text-muted-foreground mt-1">TOTAL_QUEUED</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/40 border-border/50 backdrop-blur-md relative overflow-hidden flex flex-col justify-center items-center p-8 text-center border border-primary/20">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent opacity-50" />
          <Terminal className="w-16 h-16 text-primary mb-4 opacity-80" />
          <h3 className="text-2xl font-mono tracking-widest text-primary mb-2">SAGE OS v1.0</h3>
          <p className="text-sm text-muted-foreground font-mono max-w-sm leading-relaxed">
            NEURAL ENGINE ONLINE.<br/>
            MEMORY BANKS STABLE.<br/>
            AWAITING NEXT DIRECTIVE.
          </p>
        </Card>
      </div>
    </div>
  );
}

function MetricCard({ title, value, icon: Icon, description }: { title: string; value: number; icon: any; description: string }) {
  return (
    <Card className="bg-card/40 border-border/50 backdrop-blur-md hover:border-primary/30 transition-colors group relative overflow-hidden">
      <div className="absolute top-0 left-0 w-1 h-full bg-primary/20 group-hover:bg-primary transition-colors" />
      <CardHeader className="pb-2">
        <CardTitle className="font-mono text-xs tracking-widest text-muted-foreground flex justify-between items-center">
          {title}
          <Icon className="w-4 h-4 text-primary/50 group-hover:text-primary transition-colors" />
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-4xl font-light tracking-tight text-foreground">{value}</div>
        <p className="text-xs text-muted-foreground mt-1">{description}</p>
      </CardContent>
    </Card>
  );
}
