import Link from "next/link"

const datasets = [
  {
    id: "companies",
    name: "Companies",
    description: "SEC registered companies with CIK, tickers, and metadata",
    endpoint: "/v1/companies/search",
    records: "15,000+",
    updated: "Daily",
    tags: ["Companies", "Metadata"],
  },
  {
    id: "filings",
    name: "SEC Filings",
    description: "All SEC filings including 10-K, 10-Q, 8-K, 13F, and more",
    endpoint: "/v1/filings",
    records: "5M+",
    updated: "Real-time",
    tags: ["Filings", "10-K", "10-Q", "8-K"],
  },
  {
    id: "financials",
    name: "Financial Statements",
    description: "Normalized income statements, balance sheets, and cash flows from XBRL",
    endpoint: "/v1/statements",
    records: "50M+",
    updated: "Real-time",
    tags: ["Financials", "XBRL", "Income", "Balance Sheet"],
  },
  {
    id: "13f",
    name: "13F Holdings",
    description: "Institutional investor holdings from 13F filings",
    endpoint: "/v1/holdings/13f",
    records: "10M+",
    updated: "Quarterly",
    tags: ["13F", "Holdings", "Institutions"],
  },
  {
    id: "signals",
    name: "Filing Signals",
    description: "Derived insights and events from SEC filings",
    endpoint: "/v1/signals",
    records: "1M+",
    updated: "Real-time",
    tags: ["Signals", "Events", "AI"],
  },
]

export default function Datasets() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <Link href="/" className="text-2xl font-bold">
            AI Hedge Fund
          </Link>
          <nav className="flex items-center gap-6">
            <Link href="/datasets" className="text-sm font-medium hover:underline">
              Datasets
            </Link>
            <Link href="/pricing" className="text-sm font-medium hover:underline">
              Pricing
            </Link>
            <Link href="/docs" className="text-sm font-medium hover:underline">
              Docs
            </Link>
            <Link href="/login" className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
              Sign In
            </Link>
          </nav>
        </div>
      </header>

      {/* Datasets */}
      <section className="flex-1 py-16">
        <div className="container mx-auto px-4">
          <div className="mx-auto max-w-4xl">
            <h1 className="text-4xl font-bold">Dataset Catalog</h1>
            <p className="mt-4 text-lg text-muted-foreground">
              Clean, normalized financial data from SEC EDGAR. Access via simple REST API.
            </p>

            <div className="mt-12 space-y-6">
              {datasets.map((dataset) => (
                <div key={dataset.id} className="rounded-lg border p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h2 className="text-xl font-semibold">{dataset.name}</h2>
                      <p className="mt-2 text-muted-foreground">{dataset.description}</p>

                      <div className="mt-4 flex items-center gap-6 text-sm">
                        <div>
                          <span className="text-muted-foreground">Endpoint:</span>{" "}
                          <code className="rounded bg-muted px-2 py-1 font-mono">
                            {dataset.endpoint}
                          </code>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Records:</span>{" "}
                          <span className="font-medium">{dataset.records}</span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Updated:</span>{" "}
                          <span className="font-medium">{dataset.updated}</span>
                        </div>
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2">
                        {dataset.tags.map((tag) => (
                          <span
                            key={tag}
                            className="rounded-full bg-secondary px-3 py-1 text-xs font-medium"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>

                    <Link
                      href={`/explorer?dataset=${dataset.id}`}
                      className="ml-4 rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent"
                    >
                      Try It
                    </Link>
                  </div>
                </div>
              ))}
            </div>

            {/* API Example */}
            <div className="mt-16">
              <h2 className="text-2xl font-bold">Quick Start</h2>
              <div className="mt-4 rounded-lg border bg-muted p-6">
                <pre className="text-sm">
{`# Python
import requests

response = requests.get(
    "https://api.aihedgefund.com/v1/statements",
    params={"cik": "0000320193", "stmt": "income"},
    headers={"X-API-Key": "your_api_key"}
)

data = response.json()

# JavaScript
const response = await fetch(
  "https://api.aihedgefund.com/v1/statements?cik=0000320193&stmt=income",
  { headers: { "X-API-Key": "your_api_key" } }
);

const data = await response.json();`}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t">
        <div className="container mx-auto px-4 py-8">
          <div className="text-center text-sm text-muted-foreground">
            © 2024 AI Hedge Fund. Built for the AI & finance community.
          </div>
        </div>
      </footer>
    </div>
  )
}
