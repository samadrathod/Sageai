import { ReactNode } from "react";
import { Link, useLocation } from "wouter";
import { MessageSquare, StickyNote, CheckSquare, BarChart2, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const [location] = useLocation();

  const navItems = [
    { href: "/", icon: MessageSquare, label: "Chat" },
    { href: "/notes", icon: StickyNote, label: "Notes" },
    { href: "/todos", icon: CheckSquare, label: "Tasks" },
    { href: "/dashboard", icon: BarChart2, label: "System Stats" },
  ];

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Compact Sidebar */}
      <aside className="w-16 h-full flex flex-col items-center py-6 border-r border-border/50 bg-card/50 backdrop-blur-xl shrink-0 z-10">
        <div className="mb-8 relative group">
          <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full group-hover:bg-primary/40 transition-colors duration-500" />
          <div className="relative w-10 h-10 bg-background border border-primary/30 rounded-xl flex items-center justify-center shadow-[0_0_15px_rgba(0,255,255,0.15)] group-hover:shadow-[0_0_25px_rgba(0,255,255,0.3)] transition-all duration-500">
            <Zap className="w-5 h-5 text-primary" />
          </div>
        </div>

        <nav className="flex-1 flex flex-col gap-4 w-full px-2">
          {navItems.map((item) => {
            const isActive = location === item.href;
            return (
              <Tooltip key={item.href} delayDuration={0}>
                <TooltipTrigger asChild>
                  <Link href={item.href} className="block w-full">
                    <Button
                      variant="ghost"
                      size="icon"
                      className={cn(
                        "w-full h-12 rounded-xl flex items-center justify-center transition-all duration-300",
                        isActive
                          ? "bg-primary/10 text-primary shadow-[inset_0_0_10px_rgba(0,255,255,0.1)] border border-primary/20"
                          : "text-muted-foreground hover:text-foreground hover:bg-secondary/80 border border-transparent"
                      )}
                    >
                      <item.icon className="w-5 h-5" strokeWidth={isActive ? 2.5 : 2} />
                    </Button>
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right" sideOffset={10} className="font-mono text-xs border-primary/20 bg-card/95 backdrop-blur">
                  {item.label}
                </TooltipContent>
              </Tooltip>
            );
          })}
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 h-full overflow-hidden relative">
        {/* Subtle background glow */}
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-primary/5 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-primary/5 blur-[100px] rounded-full pointer-events-none" />
        
        <div className="h-full w-full relative z-0">
          {children}
        </div>
      </main>
    </div>
  );
}
