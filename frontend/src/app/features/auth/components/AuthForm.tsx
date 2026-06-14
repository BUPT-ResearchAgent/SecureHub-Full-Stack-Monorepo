import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AlertCircle, Loader2, LogIn, UserPlus } from 'lucide-react';
import { toast } from 'sonner';
import { Alert, AlertDescription } from '@/app/components/ui/alert';
import { Checkbox } from '@/app/components/ui/checkbox';
import { Input } from '@/app/components/ui/input';
import { Label } from '@/app/components/ui/label';
import { ApiError } from '@/lib/api';
import { useAuth } from '../store';
import { PasswordField } from './PasswordField';
import { PasswordStrengthMeter, evaluatePasswordStrength } from './PasswordStrength';

type AuthFormMode = 'login' | 'register';
type FieldErrors = Partial<Record<'email' | 'password' | 'displayName' | 'confirmPassword', string>>;

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function getRedirect(search: string) {
  const value = new URLSearchParams(search).get('redirect');
  if (!value || !value.startsWith('/')) return '/workspace';
  return value;
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  return '请求失败，请稍后重试';
}

export function AuthForm({ mode }: { mode: AuthFormMode }) {
  const isRegister = mode === 'register';
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirect = useMemo(() => getRedirect(location.search), [location.search]);

  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  useEffect(() => {
    if (auth.isAuthenticated) {
      navigate('/workspace', { replace: true });
    }
  }, [auth.isAuthenticated, navigate]);

  const title = isRegister ? '创建 SecureHub 账号' : '登录 SecureHub';
  const subtitle = isRegister
    ? '注册后将直接进入工作台，并使用独立的本地演示数据分区。'
    : '使用真实账号或 demo 账号进入课程与工作台闭环。';

  const validate = () => {
    const next: FieldErrors = {};
    if (!emailPattern.test(email.trim())) {
      next.email = '邮箱格式错误';
    }
    if (isRegister && !displayName.trim()) {
      next.displayName = '显示名称不能为空';
    }
    if (isRegister && evaluatePasswordStrength(password).score < 4) {
      next.password = '密码强度不足';
    }
    if (!isRegister && !password) {
      next.password = '请输入密码';
    }
    if (isRegister && password !== confirmPassword) {
      next.confirmPassword = '两次密码不一致';
    }
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  };

  const fillDemo = () => {
    setEmail('demo-student@securehub.local');
    setPassword('SecureHub@2026');
    setRemember(true);
    setFieldErrors({});
    setFormError('');
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    if (!validate()) return;
    setLoading(true);
    try {
      if (isRegister) {
        await auth.register(
          {
            email: email.trim(),
            password,
            display_name: displayName.trim(),
          },
          { remember },
        );
        toast.success('注册成功，已进入工作台');
        navigate('/workspace', { replace: true });
      } else {
        await auth.login({ email: email.trim(), password }, { remember });
        toast.success('登录成功');
        navigate(redirect, { replace: true });
      }
    } catch (error) {
      setFormError(errorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-[#003399]">SecureHub 认证</p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-950">{title}</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">{subtitle}</p>
      </div>

      {formError && (
        <Alert variant="destructive" className="border-red-200 bg-red-50">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      <form className="space-y-4" onSubmit={handleSubmit} noValidate>
        {isRegister && (
          <div className="space-y-2">
            <Label htmlFor="display-name" className="text-slate-700">
              显示名称
            </Label>
            <Input
              id="display-name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              disabled={loading}
              placeholder="例如：李同学"
              autoComplete="name"
              aria-invalid={!!fieldErrors.displayName}
              className="h-11"
            />
            {fieldErrors.displayName && <p className="text-sm text-red-600">{fieldErrors.displayName}</p>}
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="email" className="text-slate-700">
            邮箱
          </Label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={loading}
            placeholder="name@example.com"
            autoComplete="email"
            aria-invalid={!!fieldErrors.email}
            className="h-11"
          />
          {fieldErrors.email && <p className="text-sm text-red-600">{fieldErrors.email}</p>}
        </div>

        <PasswordField
          id="password"
          label="密码"
          value={password}
          onChange={setPassword}
          disabled={loading}
          error={fieldErrors.password}
          autoComplete={isRegister ? 'new-password' : 'current-password'}
          placeholder={isRegister ? '至少 8 位，含大小写、数字和符号' : '请输入密码'}
        />

        {(isRegister || password) && <PasswordStrengthMeter password={password} />}

        {isRegister && (
          <PasswordField
            id="confirm-password"
            label="确认密码"
            value={confirmPassword}
            onChange={setConfirmPassword}
            disabled={loading}
            error={fieldErrors.confirmPassword}
            autoComplete="new-password"
            placeholder="再次输入密码"
          />
        )}

        <div className="flex items-center justify-between gap-3">
          <label htmlFor="remember" className="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
            <Checkbox
              id="remember"
              checked={remember}
              onCheckedChange={(checked) => setRemember(checked === true)}
              disabled={loading}
            />
            记住登录
          </label>
          {!isRegister && (
            <button
              type="button"
              onClick={fillDemo}
              disabled={loading}
              className="text-sm font-medium text-[#003399] hover:underline disabled:cursor-not-allowed disabled:opacity-50"
            >
              填入 demo 账号
            </button>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-[#003399] px-4 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#002a80] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : isRegister ? <UserPlus className="h-4 w-4" /> : <LogIn className="h-4 w-4" />}
          {isRegister ? '注册并进入工作台' : '登录'}
        </button>
      </form>

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm leading-6 text-slate-600">
        Demo 账号：demo-student@securehub.local / SecureHub@2026。该账号加载陈同学演示数据。
      </div>

      <p className="text-center text-sm text-slate-600">
        {isRegister ? '已有账号？' : '还没有账号？'}
        <Link
          to={`${isRegister ? '/login' : '/register'}${location.search}`}
          className="ml-1 font-medium text-[#003399] hover:underline"
        >
          {isRegister ? '去登录' : '创建账号'}
        </Link>
      </p>
    </div>
  );
}
