import {
  Tv,
  Film,
  Search,
  List,
  Podcast,
  Music,
  Cloud,
  Download,
  Train,
  HardDrive,
  Server,
  Users,
  LayoutDashboard,
  Library,
  Activity,
  Settings,
  CircleHelp,
  TerminalSquare,
  SlidersHorizontal,
  History,
  BarChart3,
  Bell,
  Save,
  Plus,
  Check,
  CheckCircle2,
  X,
  RefreshCw,
  ArrowLeft,
  PlayCircle,
  AlertTriangle,
  type LucideIcon,
  type LucideProps,
} from "lucide-react";

// Material Symbols → Lucide mapping. The HTML prototypes (stitch-export) use
// Material Symbols glyph names; the runtime app uses Lucide (per README), so
// this maps the prototype icon names onto Lucide components.
const ICON_MAP: Record<string, LucideIcon> = {
  tv: Tv,
  movie: Film,
  search: Search,
  list_alt: List,
  stream: Podcast,
  album: Music,
  cloud: Cloud,
  download: Download,
  transfer_within_a_station: Train,
  dns: HardDrive,
  lan: Server,
  group: Users,
  smart_toy: Users,
  dashboard: LayoutDashboard,
  subscriptions: Library,
  pulse_alert: Activity,
  settings: Settings,
  help: CircleHelp,
  terminal: TerminalSquare,
  tune: SlidersHorizontal,
  history: History,
  analytics: BarChart3,
  notifications_active: Bell,
  notifications: Bell,
  storage: HardDrive,
  add: Plus,
  check: Check,
  check_circle: CheckCircle2,
  close: X,
  refresh: RefreshCw,
  arrow_back: ArrowLeft,
  play_circle: PlayCircle,
  warning: AlertTriangle,
};

interface IconProps extends Omit<LucideProps, "fill"> {
  /** Material Symbol name from the prototypes (see ICON_MAP). */
  name: string;
  /** Filled variant (Material `FILL 1` equivalent). */
  fill?: boolean;
}

/**
 * Renders a Lucide icon from a Material Symbol name used in the
 * stitch-export HTML prototypes. Falls back to a warning glyph for unknown
 * names so a missing mapping never renders blank.
 */
export default function Icon({ name, fill, ...props }: IconProps) {
  const Component = ICON_MAP[name] ?? AlertTriangle;
  return (
    <Component
      fill={fill ? "currentColor" : "none"}
      {...props}
      aria-hidden="true"
    />
  );
}
