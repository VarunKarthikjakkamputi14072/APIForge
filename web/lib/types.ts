export type WeatherResponse = {
  city: string;
  temperature_c: number;
  humidity_pct: number;
  condition: string;
  wind_kph: number;
  timestamp: string;
};

export type NewsArticle = {
  title: string;
  summary: string;
  source: string;
  url: string;
  published_at: string | null;
};

export type NewsResponse = {
  articles: NewsArticle[];
  total: number;
  topic: string;
};

export type FinanceQuoteResponse = {
  symbol: string;
  price: number;
  change_pct: number;
  volume: number;
  market_cap: number | null;
  timestamp: string;
};

export type AggregateResponse = {
  city: string;
  topic: string;
  weather: WeatherResponse | null;
  news: NewsResponse | null;
  errors: Record<string, string>;
};

export type EndpointId = "weather" | "news" | "finance" | "aggregate";

export type RequestRecord = {
  id: string;
  endpoint: string;
  status: number;
  latency_ms: number;
  timestamp: string;
};

export type HourlyPoint = { hour: string; requests: number };
export type EndpointPoint = { endpoint: string; requests: number };

export type UsageSummary = {
  today: number;
  week: number;
  hourly_limit: number;
  remaining: number;
  hourly: HourlyPoint[];
  by_endpoint: EndpointPoint[];
  recent: RequestRecord[];
};
