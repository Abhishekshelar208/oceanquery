import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../routes/app_router.dart';
import '../../themes/app_theme.dart';

class MainLayout extends StatefulWidget {
  final Widget child;

  const MainLayout({
    super.key,
    required this.child,
  });

  @override
  State<MainLayout> createState() => _MainLayoutState();
}

class _MainLayoutState extends State<MainLayout> {
  @override
  Widget build(BuildContext context) {
    final bool isWideScreen = MediaQuery.of(context).size.width >= 1024;
    final String currentLocation = GoRouterState.of(context).uri.path;

    return Scaffold(
      appBar: AppBar(
        title: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.waves, color: Colors.white),
            SizedBox(width: 8),
            Text(
              'OceanQuery',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
          ],
        ),
        actions: [
          // Theme toggle button
          IconButton(
            icon: Icon(
              Theme.of(context).brightness == Brightness.light
                  ? Icons.dark_mode
                  : Icons.light_mode,
            ),
            onPressed: () {
              // TODO: Implement theme toggle
            },
            tooltip: 'Toggle theme',
          ),
          
          // Profile/Settings
          PopupMenuButton<String>(
            icon: const CircleAvatar(
              backgroundColor: AppTheme.lightBlue,
              child: Icon(Icons.person, color: Colors.white),
            ),
            onSelected: (value) {
              switch (value) {
                case 'profile':
                  // TODO: Navigate to profile
                  break;
                case 'settings':
                  // TODO: Navigate to settings
                  break;
                case 'logout':
                  context.go(AppRouter.auth);
                  break;
              }
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'profile',
                child: ListTile(
                  leading: Icon(Icons.person),
                  title: Text('Profile'),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
              const PopupMenuItem(
                value: 'settings',
                child: ListTile(
                  leading: Icon(Icons.settings),
                  title: Text('Settings'),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
              const PopupMenuDivider(),
              const PopupMenuItem(
                value: 'logout',
                child: ListTile(
                  leading: Icon(Icons.logout, color: AppTheme.error),
                  title: Text('Logout', style: TextStyle(color: AppTheme.error)),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
            ],
          ),
          const SizedBox(width: 8),
        ],
      ),
      
      // Navigation drawer for mobile/tablet
      drawer: isWideScreen ? null : _buildNavigationDrawer(currentLocation),
      
      // Body with permanent drawer for desktop
      body: isWideScreen
          ? Row(
              children: [
                _buildNavigationRail(currentLocation),
                const VerticalDivider(width: 1),
                Expanded(child: widget.child),
              ],
            )
          : widget.child,
    );
  }

  Widget _buildNavigationDrawer(String currentLocation) {
    return NavigationDrawer(
      selectedIndex: _getSelectedIndex(currentLocation),
      onDestinationSelected: _onDestinationSelected,
      children: [
        const SizedBox(height: 16),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text(
            'Navigation',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        const SizedBox(height: 8),
        ..._getNavigationDestinations(),
      ],
    );
  }

  Widget _buildNavigationRail(String currentLocation) {
    return NavigationRail(
      extended: true,
      selectedIndex: _getSelectedIndex(currentLocation),
      onDestinationSelected: _onDestinationSelected,
      destinations: [
        const NavigationRailDestination(
          icon: Icon(Icons.dashboard_outlined),
          selectedIcon: Icon(Icons.dashboard),
          label: Text('Dashboard'),
        ),
        const NavigationRailDestination(
          icon: Icon(Icons.chat_bubble_outline),
          selectedIcon: Icon(Icons.chat_bubble),
          label: Text('Chat'),
        ),
      ],
    );
  }

  List<Widget> _getNavigationDestinations() {
    return [
      const NavigationDrawerDestination(
        icon: Icon(Icons.dashboard_outlined),
        selectedIcon: Icon(Icons.dashboard),
        label: Text('Dashboard'),
      ),
      const NavigationDrawerDestination(
        icon: Icon(Icons.chat_bubble_outline),
        selectedIcon: Icon(Icons.chat_bubble),
        label: Text('Chat'),
      ),
      const SizedBox(height: 16),
      const Divider(),
      const SizedBox(height: 16),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Text(
          'Quick Actions',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ),
      const SizedBox(height: 8),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Sample Queries',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Text(
                  'Try asking: "Show me temperature profiles in the Indian Ocean"',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 8),
                ElevatedButton(
                  onPressed: () {
                    context.go(AppRouter.chat);
                    Navigator.of(context).pop(); // Close drawer
                  },
                  child: const Text('Start Chat'),
                ),
              ],
            ),
          ),
        ),
      ),
    ];
  }

  int _getSelectedIndex(String location) {
    switch (location) {
      case AppRouter.dashboard:
      case AppRouter.home:
        return 0;
      case AppRouter.chat:
        return 1;
      default:
        return 0;
    }
  }

  void _onDestinationSelected(int index) {
    switch (index) {
      case 0:
        context.go(AppRouter.dashboard);
        break;
      case 1:
        context.go(AppRouter.chat);
        break;
    }
  }
}
