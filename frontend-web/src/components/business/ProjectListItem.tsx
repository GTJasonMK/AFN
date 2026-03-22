export interface ProjectListItemModel {
  id: string;
  title: string;
  description?: string;
  status: string;
  updated_at: string;
  kind?: 'novel' | 'coding';
}
