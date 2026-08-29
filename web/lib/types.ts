export interface ScoreComponent {
  kind: string;
  label: string;
  penalty: number;
  weight: number;
  measured: number;
  unit: string;
  explanation: string;
  skipped: boolean;
}

export interface Quality {
  score: number;
  grade: string;
  verdict: string;
  duration_s: number;
  usable_seconds: number;
  usable_fraction: number;
  contaminated_seconds: number;
  components: ScoreComponent[];
  bad_channels: string[];
  n_channels: number;
  warnings: string[];
  skipped_checks: string[];
}

export interface ArtifactEvent {
  onset: number;
  duration: number;
  kind: string;
  severity: number;
  channels: string[];
}

export interface DetectorOut {
  kind: string;
  label: string;
  n_events: number;
  events: ArtifactEvent[];
  per_channel: Record<string, number>;
  threshold: number | null;
  detail: Record<string, unknown>;
  skipped_reason: string | null;
  contaminated_fraction?: number;
  per_minute?: number;
}

export interface Analysis {
  file: {
    format: string;
    duration_s: number;
    sfreq: number;
    n_channels_total: number;
    n_channels_analysed: number;
    channel_names: string[];
    assumed_microvolts: boolean;
  };
  triage: {
    kept: string[];
    excluded: Record<string, string[]>;
    kept_but_suspicious?: Record<string, string[]>;
    warnings: string[];
  };
  quality: Quality | null;
  detectors: Record<string, DetectorOut>;
  preview?: {
    duration_s: number;
    sfreq: number;
    n_shown: number;
    n_total: number;
    channels: { name: string; minmax: [number, number][] }[];
  };
  psd?: { freqs: number[]; db: number[] };
}
