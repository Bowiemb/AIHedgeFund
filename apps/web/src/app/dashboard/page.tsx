"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"

export default function Dashboard() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [apiKeys, setApiKeys] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showKeyModal, setShowKeyModal] = useState(false)
  const [newKey, setNewKey] = useState("")

  useEffect(() => {
    fetchUserData()
  }, [])

  const fetchUserData = async () => {
    const token = localStorage.getItem("access_token")

    if (!token) {
      router.push("/login")
      return
    }

    try {
      // Get user info
      const userRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!userRes.ok) throw new Error("Failed to fetch user")

      const userData = await userRes.json()
      setUser(userData.data)

      // Get API keys
      const keysRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/auth/api-keys`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!keysRes.ok) throw new Error("Failed to fetch keys")

      const keysData = await keysRes.json()
      setApiKeys(keysData.data)
    } catch (error) {
      console.error(error)
      router.push("/login")
    } finally {
      setLoading(false)
    }
  }

  const createApiKey = async () => {
    const token = localStorage.getItem("access_token")

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/auth/api-keys`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: "My API Key" }),
      })

      if (!res.ok) throw new Error("Failed to create key")

      const data = await res.json()
      setNewKey(data.data.key)
      setShowKeyModal(true)

      // Refresh keys
      fetchUserData()
    } catch (error) {
      console.error(error)
    }
  }

  const revokeKey = async (keyId: string) => {
    const token = localStorage.getItem("access_token")

    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/v1/auth/api-keys/${keyId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })

      // Refresh keys
      fetchUserData()
    } catch (error) {
      console.error(error)
    }
  }

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center">Loading...</div>
  }

  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <Link href="/" className="text-2xl font-bold">
            AI Hedge Fund
          </Link>
          <nav className="flex items-center gap-6">
            <Link href="/dashboard" className="text-sm font-medium hover:underline">
              Dashboard
            </Link>
            <Link href="/datasets" className="text-sm font-medium hover:underline">
              Datasets
            </Link>
            <Link href="/docs" className="text-sm font-medium hover:underline">
              Docs
            </Link>
            <button
              onClick={() => {
                localStorage.removeItem("access_token")
                router.push("/")
              }}
              className="text-sm font-medium hover:underline"
            >
              Sign Out
            </button>
          </nav>
        </div>
      </header>

      {/* Dashboard */}
      <div className="flex-1 py-8">
        <div className="container mx-auto px-4">
          <h1 className="text-3xl font-bold">Dashboard</h1>

          {/* User Info */}
          <div className="mt-8 rounded-lg border p-6">
            <h2 className="text-xl font-semibold">Account</h2>
            <div className="mt-4 space-y-2">
              <p><span className="text-muted-foreground">Email:</span> {user?.email}</p>
              <p><span className="text-muted-foreground">Name:</span> {user?.full_name || "Not set"}</p>
              <p><span className="text-muted-foreground">Plan:</span> Free</p>
            </div>
            <Link
              href="/pricing"
              className="mt-4 inline-block rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Upgrade Plan
            </Link>
          </div>

          {/* API Keys */}
          <div className="mt-8 rounded-lg border p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">API Keys</h2>
              <button
                onClick={createApiKey}
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Create New Key
              </button>
            </div>

            {apiKeys.length === 0 ? (
              <p className="mt-4 text-muted-foreground">No API keys yet. Create one to get started.</p>
            ) : (
              <div className="mt-4 space-y-4">
                {apiKeys.map((key) => (
                  <div key={key.id} className="flex items-center justify-between rounded-md border p-4">
                    <div>
                      <p className="font-mono text-sm">{key.key_prefix}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Created {new Date(key.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <button
                      onClick={() => revokeKey(key.id)}
                      className="text-sm text-destructive hover:underline"
                    >
                      Revoke
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Key Modal */}
      {showKeyModal && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-lg bg-background p-6">
            <h3 className="text-lg font-semibold">Your New API Key</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Copy this key now - you won't be able to see it again!
            </p>
            <div className="mt-4 rounded-md bg-muted p-4">
              <code className="break-all text-sm">{newKey}</code>
            </div>
            <button
              onClick={() => {
                navigator.clipboard.writeText(newKey)
                setShowKeyModal(false)
              }}
              className="mt-4 w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Copy and Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
