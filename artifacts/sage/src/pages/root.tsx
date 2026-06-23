import { Layout } from "@/components/layout";
import { Switch, Route } from "wouter";
import ChatPage from "@/pages/chat";
import NotesPage from "@/pages/notes";
import TodosPage from "@/pages/todos";
import DashboardPage from "@/pages/dashboard";
import MemoryPage from "@/pages/memory";

export default function Root() {
  return (
    <Layout>
      <Switch>
        <Route path="/" component={ChatPage} />
        <Route path="/notes" component={NotesPage} />
        <Route path="/todos" component={TodosPage} />
        <Route path="/dashboard" component={DashboardPage} />
        <Route path="/memory" component={MemoryPage} />
      </Switch>
    </Layout>
  );
}
