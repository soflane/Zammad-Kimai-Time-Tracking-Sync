import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function Dashboard() {
  return (
    <div className="p-4 space-y-4">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <Card>
        <CardHeader>
          <CardTitle>Sync Status</CardTitle>
          <CardDescription>Overview of recent syncs and conflicts</CardDescription>
        </CardHeader>
        <CardContent>
          <p>Placeholder for dashboard stats</p>
          <Button>Run Sync</Button>
        </CardContent>
      </Card>
    </div>
  )
}
