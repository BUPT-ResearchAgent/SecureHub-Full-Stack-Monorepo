import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { AlertCircle, Loader2, LogIn, UserPlus } from 'lucide-react';
import { toast } from 'sonner';
import { Alert, AlertDescription } from '@/app/components/ui/alert';
import { Checkbox } from '@/app/components/ui/checkbox';
import { Input } from '@/app/components/ui/input';
import { Label } from '@/app/components/ui/label';
import { ApiError } from '@/lib/api';
import * as authApi from '../api';
import { useAuth } from '../store';
import { PasswordField } from './PasswordField';
import { PasswordStrengthMeter, evaluatePasswordStrength } from './PasswordStrength';
import { DEMO_ACCOUNTS, getDemoAccount, resolvePostLoginPath } from '../demoAccounts';

type AuthFormMode = 'login' | 'register';
type FieldErrors = Partial<
  Record<'email' | 'password' | 'displayName' | 'confirmPassword' | 'newPassword' | 'confirmNewPassword', string>
>;

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
  const hasRequestedRedirect = useMemo(
    () => new URLSearchParams(location.search).has('redirect'),
    [location.search],
  );
  const requestedDemo = useMemo(
    () => getDemoAccount(new URLSearchParams(location.search).get('demo')),
    [location.search],
  );

  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [remediationRequired, setRemediationRequired] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [selectedDemoId, setSelectedDemoId] = useState<string | null>(
    requestedDemo?.id ?? null,
  );

  useEffect(() => {
    if (requestedDemo) {
      setSelectedDemoId(requestedDemo.id);
      setEmail(requestedDemo.email);
      setPassword(requestedDemo.password);
      setRemember(true);
      setFieldErrors({});
      setFormError('');
      setRemediationRequired(false);
      setNewPassword('');
      setConfirmNewPassword('');
    }
  }, [requestedDemo]);

  useEffect(() => {
    if (auth.isAuthenticated && !requestedDemo) {
      navigate(
        resolvePostLoginPath(
          auth.user?.role ?? 'student',
          hasRequestedRedirect ? redirect : null,
        ),
        { replace: true },
      );
    }
  }, [auth.isAuthenticated, auth.user?.role, hasRequestedRedirect, navigate, redirect, requestedDemo]);

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

  const validateRemediation = () => {
    const next: FieldErrors = {};
    if (!emailPattern.test(email.trim())) {
      next.email = '邮箱格式错误';
    }
    if (!password) {
      next.password = '请先填写当前密码';
    }
    if (evaluatePasswordStrength(newPassword).score < 4) {
      next.newPassword = '新密码强度不足';
    }
    if (newPassword !== confirmNewPassword) {
      next.confirmNewPassword = '两次新密码不一致';
    }
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  };

  const completeRemediation = async () => {
    setFormError('');
    if (!validateRemediation()) return;
    setLoading(true);
    try {
      await authApi.remediatePassword({
        email: email.trim(),
        current_password: password,
        new_password: newPassword,
        reason: '登录前完成当前密码策略整改。',
      });
      setPassword(newPassword);
      setFieldErrors({});
      setRemediationRequired(false);
      const signedInUser = await auth.login(
        { email: email.trim(), password: newPassword },
        { remember },
      );
      toast.success('密码整改完成，已重新登录');
      navigate(
        resolvePostLoginPath(
          signedInUser.role,
          hasRequestedRedirect ? redirect : null,
        ),
        { replace: true },
      );
    } catch (error) {
      setFormError(errorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  const selectDemo = (id: string) => {
    const account = getDemoAccount(id);
    if (!account) return;
    setSelectedDemoId(account.id);
    setEmail(account.email);
    setPassword(account.password);
    setRemember(true);
    setFieldErrors({});
    setFormError('');
    setRemediationRequired(false);
    setNewPassword('');
    setConfirmNewPassword('');
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
        const signedInUser = await auth.login({ email: email.trim(), password }, { remember });
        setRemediationRequired(false);
        toast.success('登录成功');
        navigate(
          resolvePostLoginPath(
            signedInUser.role,
            hasRequestedRedirect ? redirect : null,
          ),
          { replace: true },
        );
      }
    } catch (error) {
      if (!isRegister && error instanceof ApiError && error.code === 'PASSWORD_REMEDIATION_REQUIRED') {
        setRemediationRequired(true);
      }
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

      {!isRegister && (
        <section className="rounded-xl border border-brand-blue-100 bg-brand-blue-50/40 p-3.5">
          <div className="mb-3">
            <h2 className="text-sm font-semibold text-slate-900">选择演示身份</h2>
            <p className="mt-0.5 text-xs leading-5 text-slate-600">
              选择后自动填入对应账号，登录后进入该身份的演示工作台。
            </p>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {DEMO_ACCOUNTS.map((account) => {
              const Icon = account.icon;
              const selected = account.id === selectedDemoId;
              const remediationDemo = account.tone === 'remediation';
              return (
                <button
                  key={account.id}
                  type="button"
                  onClick={() => selectDemo(account.id)}
                  disabled={loading}
                  aria-pressed={selected}
                  className={`group rounded-lg border p-3 text-left transition-all disabled:cursor-not-allowed disabled:opacity-60 ${
                    selected
                      ? remediationDemo
                        ? 'border-amber-500 bg-amber-50 shadow-sm'
                        : 'border-brand-blue-600 bg-white shadow-sm'
                      : remediationDemo
                        ? 'border-amber-200 bg-amber-50/70 hover:-translate-y-0.5 hover:border-amber-400 hover:bg-amber-50'
                        : 'border-slate-200 bg-white/70 hover:-translate-y-0.5 hover:border-brand-blue-200 hover:bg-white'
                  } ${account.fullWidth ? 'sm:col-span-2' : ''}`}
                >
                  <span
                    className={`flex h-7 w-7 items-center justify-center rounded-md transition-colors ${
                      selected
                        ? remediationDemo
                          ? 'bg-amber-600 text-white'
                          : 'bg-brand-blue-600 text-white'
                        : remediationDemo
                          ? 'bg-amber-100 text-amber-700 group-hover:bg-amber-600 group-hover:text-white'
                          : 'bg-slate-100 text-slate-600 group-hover:bg-brand-blue-600 group-hover:text-white'
                    }`}
                  >
                    <Icon className="h-4 w-4" aria-hidden />
                  </span>
                  <span className="mt-2 block text-sm font-semibold text-slate-800">{account.label}</span>
                  <span className="mt-0.5 block text-[11px] leading-4 text-slate-500">{account.description}</span>
                </button>
              );
            })}
          </div>
        </section>
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

        {!isRegister && remediationRequired && (
          <section className="space-y-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
            <div>
              <h2 className="text-sm font-semibold text-amber-950">完成密码整改</h2>
              <p className="mt-1 text-xs leading-5 text-amber-900">
                请使用上方当前密码验证身份，并设置符合当前策略的新密码。完成后系统才会签发登录会话。
              </p>
            </div>
            <PasswordField
              id="new-password"
              label="新密码"
              value={newPassword}
              onChange={setNewPassword}
              disabled={loading}
              error={fieldErrors.newPassword}
              autoComplete="new-password"
              placeholder="至少 8 位，含大小写、数字和符号"
            />
            <PasswordStrengthMeter password={newPassword} />
            <PasswordField
              id="confirm-new-password"
              label="确认新密码"
              value={confirmNewPassword}
              onChange={setConfirmNewPassword}
              disabled={loading}
              error={fieldErrors.confirmNewPassword}
              autoComplete="new-password"
              placeholder="再次输入新密码"
            />
            <button
              type="button"
              onClick={() => void completeRemediation()}
              disabled={loading}
              className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-amber-700 px-4 text-sm font-semibold text-white transition-colors hover:bg-amber-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <LogIn className="h-4 w-4" />}
              更新密码并重新登录
            </button>
          </section>
        )}

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
          {!isRegister && <span className="text-xs text-slate-600">演示账号密码已自动填入</span>}
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

      {!isRegister && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm leading-6 text-slate-600">
          演示身份使用独立账号和固定示例数据；普通账号默认进入学生工作台。
        </div>
      )}

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
