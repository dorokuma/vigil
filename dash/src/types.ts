export interface EnrichedServer {
  name: string;
  location: string;
  online: boolean;
  latency: number | string | null;
  packetLoss: number;
  uptime: string;
  cpu: number;
  memory: number;
  disk: number;
}
