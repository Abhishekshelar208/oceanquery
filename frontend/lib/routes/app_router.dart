import 'package:go_router/go_router.dart';
import 'package:flutter/material.dart';

import '../screens/auth/auth_screen.dart';
import '../screens/chat/chat_screen.dart';
import '../screens/dashboard/advanced_dashboard_screen.dart';
import '../screens/dashboard/dashboard_screen.dart';
import '../widgets/common/main_layout.dart';

class AppRouter {
  static const String auth = '/auth';
  static const String chat = '/chat';
  static const String dashboard = '/dashboard';
  static const String home = '/';

  static GoRouter get router => _router;

  static final GoRouter _router = GoRouter(
    initialLocation: home,
    routes: [
      // Authentication route
      GoRoute(
        path: auth,
        name: 'auth',
        builder: (context, state) => const AuthScreen(),
      ),
      
      // Main app shell with navigation
      ShellRoute(
        builder: (context, state, child) => MainLayout(child: child),
        routes: [
          // Home/Dashboard
          GoRoute(
            path: home,
            name: 'home',
            builder: (context, state) => const AdvancedDashboardScreen(),
          ),
          
          // Dashboard
          GoRoute(
            path: dashboard,
            name: 'dashboard',
            builder: (context, state) => const AdvancedDashboardScreen(),
          ),
          
          // Chat
          GoRoute(
            path: chat,
            name: 'chat',
            builder: (context, state) => const ChatScreen(),
          ),
        ],
      ),
    ],
    
    // Redirect logic for authentication
    redirect: (context, state) {
      // TODO: Implement authentication check
      // For now, allow all routes
      return null;
    },
    
    // Error page
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Page Not Found',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'The page "${state.uri.path}" does not exist.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => context.go(home),
              child: const Text('Go Home'),
            ),
          ],
        ),
      ),
    ),
  );
}
