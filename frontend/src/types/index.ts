export type UserRole = "ADMIN" | "MANAGER" | "MEMBER";

export type WorkItemType = "BUG" | "FEATURE" | "TASK" | "INCIDENT";

export type WorkItemPriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type WorkItemStatus = "OPEN" | "IN_PROGRESS" | "BLOCKED" | "RESOLVED";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TeamMembership {
  id: number;
  team_id: number;
  user_id: number;
  team_role: string;
  created_at: string;
  user?: User;
}

export interface Team {
  id: number;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  memberships: TeamMembership[];
}

export interface Comment {
  id: number;
  work_item_id: number;
  author_id: number;
  content: string;
  created_at: string;
  updated_at: string;
  author?: User;
}

export interface ActivityLog {
  id: number;
  work_item_id: number;
  actor_id: number;
  action: string;
  field_name?: string | null;
  previous_value?: string | null;
  new_value?: string | null;
  timestamp: string;
  actor?: User;
}

export interface WorkItem {
  id: number;
  title: string;
  description?: string | null;
  item_type: WorkItemType;
  priority: WorkItemPriority;
  status: WorkItemStatus;
  team_id: number;
  assignee_id?: number | null;
  reporter_id: number;
  due_date?: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  team?: Team;
  assignee?: User | null;
  reporter?: User;
  comments?: Comment[];
  activity_logs?: ActivityLog[];
}

export interface WorkItemListResponse {
  items: WorkItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DashboardStats {
  total_work_items: number;
  open_and_in_progress: number;
  critical_priority: number;
  assigned_to_me: number;
  awaiting_action_blocked: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  recent_activities: ActivityLog[];
}
