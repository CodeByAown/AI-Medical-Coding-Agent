import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Check for token in cookies (set by client after login)
  const token = request.cookies.get("nh_token")?.value

  const isAuthRoute = pathname.startsWith("/login") || pathname.startsWith("/register")
  const isDashboardRoute = pathname.startsWith("/dashboard")

  if (isDashboardRoute && !token) {
    return NextResponse.redirect(new URL("/login", request.url))
  }

  if (isAuthRoute && token) {
    return NextResponse.redirect(new URL("/dashboard", request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/register"],
}
