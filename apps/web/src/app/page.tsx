import Link from "next/link"

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="text-2xl font-bold">
            AI Hedge Fund
          </div>
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

      {/* Hero */}
      <section className="flex-1">
        <div className="container mx-auto px-4 py-24">
          <div className="mx-auto max-w-3xl text-center">
            <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">
              Financial Data API for
              <span className="text-primary"> AI & Quant Traders</span>
            </h1>
            <p className="mt-6 text-lg text-muted-foreground">
              Access clean, normalized SEC EDGAR data through a simple API. Build trading strategies,
              run backtests, and execute trades with institutional-grade infrastructure.
            </p>
            <div className="mt-10 flex items-center justify-center gap-4">
              <Link
                href="/signup"
                className="rounded-md bg-primary px-8 py-3 text-sm font-semibold text-primary-foreground shadow hover:bg-primary/90"
              >
                Get Started Free
              </Link>
              <Link
                href="/docs"
                className="rounded-md border px-8 py-3 text-sm font-semibold hover:bg-accent"
              >
                View Docs
              </Link>
            </div>
          </div>

          {/* Features */}
          <div className="mx-auto mt-24 grid max-w-5xl gap-8 md:grid-cols-3">
            <div className="rounded-lg border p-6">
              <h3 className="text-lg font-semibold">SEC Data API</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Clean, normalized financial data from SEC EDGAR filings. 10-K, 10-Q, 13F, and more.
              </p>
            </div>
            <div className="rounded-lg border p-6">
              <h3 className="text-lg font-semibold">AI Backtesting</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Test trading strategies with historical data. Factor models, signals, and portfolio optimization.
              </p>
            </div>
            <div className="rounded-lg border p-6">
              <h3 className="text-lg font-semibold">Paper & Live Trading</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Execute trades via Interactive Brokers. Start with paper trading, scale to live.
              </p>
            </div>
          </div>

          {/* Code Example */}
          <div className="mx-auto mt-24 max-w-3xl">
            <h2 className="text-2xl font-bold">Simple to Use</h2>
            <div className="mt-4 rounded-lg border bg-muted p-6">
              <pre className="text-sm">
{`import requests

# Search companies
companies = requests.get(
  "https://api.aihedgefund.com/v1/companies/search?q=Apple"
)

# Get financial statements
statements = requests.get(
  "https://api.aihedgefund.com/v1/statements",
  params={"cik": "0000320193", "stmt": "income"}
)

# Get 13F holdings
holdings = requests.get(
  "https://api.aihedgefund.com/v1/holdings/13f?cik=0001067983"
)`}
              </pre>
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
