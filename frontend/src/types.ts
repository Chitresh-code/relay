export type SkillGroup = { category: string; skills: string[] };
export type GithubRepoItem = { name: string; description: string; url: string; language: string; updated: string };
export type ExperienceItem = { role: string; company: string; period: string; bullets: string[] };
export type EducationItem = { degree: string; school: string; period: string };
export type ContactItem = { label: string; value: string };
export type ResumeCard = { name: string; format: string; updated: string; size: string; url?: string };
export type InfoCard = { quote: string };
export type RequestContactCard = { reason: string };

export type ToolName =
  | "show_skills"
  | "show_projects"
  | "show_experience"
  | "show_education"
  | "show_contact"
  | "show_resume"
  | "show_info"
  | "request_contact";

export type ComponentPayload = { tool: ToolName; content: any };

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  component?: ComponentPayload;
};
