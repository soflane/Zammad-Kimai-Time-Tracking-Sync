import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { Loader2, Mail, Lock, LogIn } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setError('Please fill in all fields');
      return;
    }
    setIsLoading(true);
    setError('');
    try {
      await login(username, password);
      toast({
        title: "Login successful",
        description: "Welcome to Zammad Sync Dashboard!",
      });
      navigate('/');
    } catch (error: any) {
      const msg = error.response?.data?.detail || 'Invalid credentials. Please try again.';
      setError(msg);
      toast({
        title: "Login failed",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-muted/20 to-background p-4">
      <Card className="w-full max-w-md shadow-floating border-border/50 card-hover">
        <CardHeader className="text-center space-y-4 pb-6">
          <div className="flex items-center justify-center w-20 h-20 bg-gradient-to-br from-primary to-primary/80 rounded-full mx-auto">
            <LogIn className="h-10 w-10 text-primary-foreground" />
          </div>
          <div className="space-y-1">
            <CardTitle className="text-3xl font-bold gradient-text">Welcome Back</CardTitle>
            <CardDescription className="text-lg text-muted-foreground">
              Sign in to your Zammad-Kimai Sync account
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-4">
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <Input
                  id="username"
                  type="text"
                  placeholder="Username (admin)"
                  value={username}
                  onChange={(e) => {
                    setUsername(e.target.value);
                    if (error) setError('');
                  }}
                  className="pl-12 h-12 text-base border-border/50 focus:border-primary/50 transition-colors"
                  required
                />
              </div>
              {error && username === '' && <p className="text-sm text-destructive mt-2">Username is required</p>}
            </div>
            <div className="space-y-4">
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  placeholder="Password (changeme)"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError('');
                  }}
                  className="pl-12 h-12 text-base border-border/50 focus:border-primary/50 transition-colors"
                  required
                />
              </div>
              {error && password === '' && <p className="text-sm text-destructive mt-2">Password is required</p>}
            </div>
            {error && username !== '' && password !== '' && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <p className="text-sm text-destructive text-center">{error}</p>
              </div>
            )}
            <Button 
              type="submit" 
              className="w-full h-12 text-base btn-modern gradient-bg text-primary-foreground hover:shadow-floating" 
              disabled={isLoading || !username || !password}
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>
          <div className="text-center text-sm text-muted-foreground bg-muted/30 p-3 rounded-lg">
            Demo credentials: <span className="font-mono">admin</span> / <span className="font-mono">changeme</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
