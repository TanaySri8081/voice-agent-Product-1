import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { Bot, Loader2 } from "lucide-react";

export default function Register() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [clinicName, setClinicName] = useState("");
  const [did, setDid] = useState("");
  const { register, error, loading } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password || !name || !clinicName) return;
    const success = await register(email, password, name, clinicName, did);
    if (success) {
      navigate("/dashboard");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8 rounded-3xl border border-gray-200 bg-white p-8 shadow-xl shadow-gray-900/5">
        <div className="flex flex-col items-center">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-gray-950 text-white shadow-lg shadow-gray-950/20">
            <Bot className="h-6 w-6" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-semibold tracking-tight text-gray-950">
            Onboard your clinic
          </h2>
          <p className="mt-2 text-center text-sm text-gray-500">
            Get started with VoxPilot AI Medical Receptionist
          </p>
        </div>

        {error && (
          <div className="rounded-2xl bg-red-50 p-4 text-sm text-red-600 border border-red-100">
            {error}
          </div>
        )}

        <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-3">
            <div>
              <label htmlFor="clinic-name" className="text-sm font-medium text-gray-700">
                Clinic / Hospital Name
              </label>
              <input
                id="clinic-name"
                name="clinicName"
                type="text"
                required
                className="mt-1 block w-full rounded-2xl border border-gray-200 px-4 py-2.5 text-gray-900 placeholder-gray-400 focus:border-gray-950 focus:outline-none focus:ring-1 focus:ring-gray-950 sm:text-sm"
                placeholder="Apex Dental Care"
                value={clinicName}
                onChange={(e) => setClinicName(e.target.value)}
              />
            </div>
            
            <div>
              <label htmlFor="did-number" className="text-sm font-medium text-gray-700">
                Vobiz DID Number (Optional)
              </label>
              <input
                id="did-number"
                name="did"
                type="text"
                className="mt-1 block w-full rounded-2xl border border-gray-200 px-4 py-2.5 text-gray-900 placeholder-gray-400 focus:border-gray-950 focus:outline-none focus:ring-1 focus:ring-gray-950 sm:text-sm"
                placeholder="+918045671200"
                value={did}
                onChange={(e) => setDid(e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="doctor-name" className="text-sm font-medium text-gray-700">
                Doctor Name
              </label>
              <input
                id="doctor-name"
                name="name"
                type="text"
                required
                className="mt-1 block w-full rounded-2xl border border-gray-200 px-4 py-2.5 text-gray-900 placeholder-gray-400 focus:border-gray-950 focus:outline-none focus:ring-1 focus:ring-gray-950 sm:text-sm"
                placeholder="Dr. Shreyas Raj"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="email-address" className="text-sm font-medium text-gray-700">
                Email Address
              </label>
              <input
                id="email-address"
                name="email"
                type="email"
                required
                className="mt-1 block w-full rounded-2xl border border-gray-200 px-4 py-2.5 text-gray-900 placeholder-gray-400 focus:border-gray-950 focus:outline-none focus:ring-1 focus:ring-gray-950 sm:text-sm"
                placeholder="doctor@apex.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="password" className="text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="mt-1 block w-full rounded-2xl border border-gray-200 px-4 py-2.5 text-gray-900 placeholder-gray-400 focus:border-gray-950 focus:outline-none focus:ring-1 focus:ring-gray-950 sm:text-sm"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={loading}
              className="flex w-full justify-center rounded-2xl bg-gray-950 px-4 py-3 text-sm font-semibold text-white shadow hover:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-950 disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              ) : (
                "Register & Onboard"
              )}
            </button>
          </div>
        </form>

        <p className="text-center text-sm text-gray-500">
          Already registered?{" "}
          <Link to="/login" className="font-semibold text-gray-950 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
