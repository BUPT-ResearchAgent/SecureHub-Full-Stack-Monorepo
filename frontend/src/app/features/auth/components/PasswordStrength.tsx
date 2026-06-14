export type PasswordStrength = {
  score: number;
  label: string;
  hint: string;
};

export function evaluatePasswordStrength(password: string): PasswordStrength {
  const checks = [
    password.length >= 8,
    /[a-z]/.test(password) && /[A-Z]/.test(password),
    /\d/.test(password),
    /[^A-Za-z0-9]/.test(password),
  ];
  const score = checks.filter(Boolean).length;
  if (!password) return { score: 0, label: '未填写', hint: '至少 8 位，包含大小写、数字和符号' };
  if (score <= 2) return { score, label: '不足', hint: '建议补充大小写、数字和符号' };
  if (score === 3) return { score, label: '良好', hint: '再加入一种字符类型会更稳妥' };
  return { score, label: '强', hint: '满足 SecureHub 当前密码策略' };
}

export function PasswordStrengthMeter({ password }: { password: string }) {
  const strength = evaluatePasswordStrength(password);
  const tone =
    strength.score <= 2
      ? 'bg-red-500'
      : strength.score === 3
        ? 'bg-amber-500'
        : 'bg-emerald-500';

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-4 gap-1" aria-hidden="true">
        {[0, 1, 2, 3].map((index) => (
          <div
            key={index}
            className={`h-1.5 rounded-full ${index < strength.score ? tone : 'bg-slate-200'}`}
          />
        ))}
      </div>
      <div className="flex items-start justify-between gap-3 text-xs">
        <span className="font-medium text-slate-700">密码强度：{strength.label}</span>
        <span className="text-right text-slate-500">{strength.hint}</span>
      </div>
    </div>
  );
}
