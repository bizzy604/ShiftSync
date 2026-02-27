/**
 * @file /apps/web/src/pages/LoginPage.tsx
 *
 * @description
 * UI page module for `LoginPage` workflows and role-specific interaction flows.
 *
 * @dependencies
 * - (No in-repo dependents detected.)
 *
 * @importance
 * This module defines user-facing workflows; changes here affect day-to-day product
 * usability.
 */

import React, { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react';

import { useAuth } from '../auth/AuthContext';

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login(email, password);
      navigate(`/${user.role}`);
    } catch {
      setError('Invalid email or password. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-bg">
      <div className="w-full max-w-[440px] mx-4">
        <form
          onSubmit={onSubmit}
          className="bg-white rounded-2xl shadow-2xl p-8 md:p-10 animate-fade-in"
        >
          {/* Logo */}
          <div className="flex items-center justify-center gap-3 mb-2">
            <div className="w-10 h-10 bg-navy rounded-xl flex items-center justify-center">
              <Calendar size={22} className="text-teal-light" />
            </div>
            <h1 className="text-2xl font-bold text-navy tracking-tight">ShiftSync</h1>
          </div>
          <p className="text-center text-sm text-gray-500 mb-8">
            Restaurant Scheduling Platform
          </p>

          {/* Email */}
          <div className="mb-4">
            <label htmlFor="login-email" className="block text-sm font-medium text-navy mb-1.5">
              Email address
            </label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@coastaleats.com"
              className="w-full px-4 py-3 rounded-lg border border-border-gray bg-gray-50 text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-teal/40 focus:border-teal transition-base text-sm"
            />
          </div>

          {/* Password */}
          <div className="mb-6">
            <label htmlFor="login-password" className="block text-sm font-medium text-navy mb-1.5">
              Password
            </label>
            <div className="relative">
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full px-4 py-3 rounded-lg border border-border-gray bg-gray-50 text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-teal/40 focus:border-teal transition-base text-sm pr-12"
              />
              <button
                type="button"
                onClick={() => setShowPassword((p) => !p)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-base"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-4 px-4 py-3 rounded-lg bg-danger-50 border border-danger/20 flex items-start gap-3 animate-fade-in">
              <AlertCircle size={18} className="text-danger mt-0.5 flex-shrink-0" />
              <p className="text-sm text-danger font-medium">{error}</p>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3 rounded-lg bg-teal text-white font-semibold text-sm hover:bg-teal-dark focus:ring-2 focus:ring-teal/40 disabled:opacity-60 disabled:cursor-not-allowed transition-base flex items-center justify-center gap-2"
          >
            {submitting ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                Signing in…
              </>
            ) : (
              'Sign in'
            )}
          </button>

          {/* Forgot password */}
          <div className="mt-4 text-right">
            <button type="button" className="text-sm text-gray-500 hover:text-teal transition-base">
              Forgot password?
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
