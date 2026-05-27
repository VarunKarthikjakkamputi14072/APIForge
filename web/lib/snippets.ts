import type { CodeTab } from "@/components/CodeSnippet";

export type SnippetSpec = {
  baseUrl: string;
  apiKey: string;
  path: string;
};

export function buildLanguageSnippets({ baseUrl, apiKey, path }: SnippetSpec): CodeTab[] {
  const url = `${baseUrl}${path}`;
  return [
    {
      label: "curl",
      language: "shell",
      code: `curl -s "${url}" \\
  -H "X-API-Key: ${apiKey}" | jq`,
    },
    {
      label: "Python",
      language: "python",
      code: `import httpx

API_KEY = "${apiKey}"
BASE = "${baseUrl}"

response = httpx.get(
    f"{BASE}${path}",
    headers={"X-API-Key": API_KEY},
    timeout=10.0,
)
response.raise_for_status()
print(response.json())`,
    },
    {
      label: "JavaScript",
      language: "javascript",
      code: `const apiKey = "${apiKey}";
const res = await fetch("${url}", {
  headers: { "X-API-Key": apiKey },
});
if (!res.ok) {
  throw new Error(\`APIForge returned \${res.status}\`);
}
const data = await res.json();
console.log(data);`,
    },
  ];
}
