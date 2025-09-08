import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../routes/app_router.dart';
import '../../themes/app_theme.dart';
import '../../widgets/charts/temperature_chart.dart';
import '../../widgets/maps/argo_map.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  Widget build(BuildContext context) {
    final bool isWideScreen = MediaQuery.of(context).size.width >= 1024;
    
    return Scaffold(
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Welcome header
            _buildWelcomeHeader(context),
            const SizedBox(height: 24),
            
            // Quick stats cards
            _buildQuickStats(context, isWideScreen),
            const SizedBox(height: 24),
            
            // Main content grid
            if (isWideScreen)
              _buildWideScreenLayout(context)
            else
              _buildNarrowScreenLayout(context),
          ],
        ),
      ),
    );
  }

  Widget _buildWelcomeHeader(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Ocean Data Dashboard',
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 8),
        Text(
          'Explore ARGO float data through interactive visualizations and AI-powered chat',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            color: Colors.grey[600],
          ),
        ),
        const SizedBox(height: 16),
        ElevatedButton.icon(
          onPressed: () => context.go(AppRouter.chat),
          icon: const Icon(Icons.chat_bubble_outline),
          label: const Text('Start AI Chat'),
        ),
      ],
    );
  }

  Widget _buildQuickStats(BuildContext context, bool isWideScreen) {
    final stats = [
      _StatCard(
        title: 'Active Floats',
        value: '3,847',
        subtitle: 'Currently transmitting',
        icon: Icons.sensors,
        color: AppTheme.primaryBlue,
      ),
      _StatCard(
        title: 'Data Points',
        value: '2.1M',
        subtitle: 'Temperature & salinity',
        icon: Icons.analytics,
        color: AppTheme.oceanTeal,
      ),
      _StatCard(
        title: 'Ocean Coverage',
        value: '89%',
        subtitle: 'Global ocean monitoring',
        icon: Icons.public,
        color: AppTheme.lightBlue,
      ),
      _StatCard(
        title: 'Last Update',
        value: '2h ago',
        subtitle: 'Real-time data sync',
        icon: Icons.update,
        color: AppTheme.accent,
      ),
    ];

    if (isWideScreen) {
      return Row(
        children: stats
            .map((stat) => Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(right: 16),
                    child: _buildStatCard(stat),
                  ),
                ))
            .toList(),
      );
    } else {
      return Column(
        children: [
          Row(
            children: [
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: _buildStatCard(stats[0]),
                ),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(left: 8),
                  child: _buildStatCard(stats[1]),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: _buildStatCard(stats[2]),
                ),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(left: 8),
                  child: _buildStatCard(stats[3]),
                ),
              ),
            ],
          ),
        ],
      );
    }
  }

  Widget _buildStatCard(_StatCard stat) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  stat.icon,
                  color: stat.color,
                  size: 24,
                ),
                const SizedBox(width: 8),
                Text(
                  stat.title,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              stat.value,
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            Text(
              stat.subtitle,
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[600],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildWideScreenLayout(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Left column - Charts
        Expanded(
          flex: 2,
          child: Column(
            children: [
              _buildTemperatureChart(),
              const SizedBox(height: 16),
              _buildRecentActivity(),
            ],
          ),
        ),
        const SizedBox(width: 16),
        
        // Right column - Map
        Expanded(
          flex: 3,
          child: _buildMapCard(),
        ),
      ],
    );
  }

  Widget _buildNarrowScreenLayout(BuildContext context) {
    return Column(
      children: [
        _buildMapCard(),
        const SizedBox(height: 16),
        _buildTemperatureChart(),
        const SizedBox(height: 16),
        _buildRecentActivity(),
      ],
    );
  }

  Widget _buildMapCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.map, color: AppTheme.primaryBlue),
                const SizedBox(width: 8),
                Text(
                  'ARGO Float Locations',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.fullscreen),
                  onPressed: () {
                    // TODO: Open full-screen map
                  },
                  tooltip: 'Full screen',
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 400,
              child: const ArgoMap(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTemperatureChart() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.thermostat, color: AppTheme.accent),
                const SizedBox(width: 8),
                Text(
                  'Temperature Profiles',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 300,
              child: const TemperatureChart(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecentActivity() {
    final activities = [
      'New data from Float 2902755 (Indian Ocean)',
      'Temperature anomaly detected near 15°S, 78°E',
      'Chat query: "Salinity trends in Arabian Sea"',
      'Data export completed: 450 profiles',
      'System update: Enhanced ML models deployed',
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.history, color: AppTheme.oceanTeal),
                const SizedBox(width: 8),
                Text(
                  'Recent Activity',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 16),
            for (final activity in activities.take(5)) Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: const BoxDecoration(
                      color: AppTheme.lightBlue,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      activity,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () {
                // TODO: Show full activity log
              },
              child: const Text('View all activity'),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatCard {
  final String title;
  final String value;
  final String subtitle;
  final IconData icon;
  final Color color;

  const _StatCard({
    required this.title,
    required this.value,
    required this.subtitle,
    required this.icon,
    required this.color,
  });
}
