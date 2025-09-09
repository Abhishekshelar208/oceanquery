import 'package:flutter/material.dart';
import '../../themes/app_theme.dart';
import '../../services/data_update_service.dart';

class DataStatusWidget extends StatefulWidget {
  final bool showDetails;
  final bool showControls;

  const DataStatusWidget({
    super.key,
    this.showDetails = true,
    this.showControls = false,
  });

  @override
  State<DataStatusWidget> createState() => _DataStatusWidgetState();
}

class _DataStatusWidgetState extends State<DataStatusWidget> {
  final DataUpdateService _updateService = DataUpdateService();

  @override
  void initState() {
    super.initState();
    _updateService.addListener(_onUpdateServiceChanged);
  }

  @override
  void dispose() {
    _updateService.removeListener(_onUpdateServiceChanged);
    super.dispose();
  }

  void _onUpdateServiceChanged() {
    if (mounted) {
      setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(),
            if (widget.showDetails) ...[
              const SizedBox(height: 12),
              _buildStatusDetails(),
            ],
            if (widget.showControls) ...[
              const SizedBox(height: 16),
              _buildControls(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        _buildStatusIcon(),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Data Status',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: AppTheme.primaryBlue,
                ),
              ),
              Text(
                _updateService.statusDisplayText,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: _getStatusColor(),
                ),
              ),
            ],
          ),
        ),
        _buildActionButton(),
      ],
    );
  }

  Widget _buildStatusIcon() {
    IconData icon;
    Color color;
    
    switch (_updateService.status) {
      case DataUpdateStatus.idle:
        icon = Icons.pause_circle_outline;
        color = Colors.grey;
        break;
      case DataUpdateStatus.checking:
      case DataUpdateStatus.updating:
        icon = Icons.sync;
        color = AppTheme.primaryBlue;
        break;
      case DataUpdateStatus.success:
        icon = Icons.check_circle_outline;
        color = AppTheme.success;
        break;
      case DataUpdateStatus.error:
        icon = Icons.error_outline;
        color = AppTheme.error;
        break;
    }

    Widget iconWidget = Icon(icon, color: color, size: 24);

    // Add rotation animation for updating status
    if (_updateService.status == DataUpdateStatus.checking ||
        _updateService.status == DataUpdateStatus.updating) {
      return RotationTransition(
        turns: Tween(begin: 0.0, end: 1.0).animate(
          AnimationController(
            duration: const Duration(seconds: 2),
            vsync: Navigator.of(context),
          )..repeat(),
        ),
        child: iconWidget,
      );
    }

    return iconWidget;
  }

  Widget _buildStatusDetails() {
    return Column(
      children: [
        _buildDetailRow(
          icon: Icons.access_time,
          label: 'Last Update',
          value: _updateService.lastUpdateDisplayText,
        ),
        const SizedBox(height: 8),
        _buildDetailRow(
          icon: Icons.schedule,
          label: 'Update Interval',
          value: '${_updateService.updateInterval.inMinutes} minutes',
        ),
        const SizedBox(height: 8),
        _buildDetailRow(
          icon: Icons.play_circle_outline,
          label: 'Auto Update',
          value: _updateService.isRunning ? 'On' : 'Off',
        ),
        if (_updateService.error != null) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppTheme.error.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: AppTheme.error.withValues(alpha: 0.3)),
            ),
            child: Row(
              children: [
                Icon(Icons.error, size: 16, color: AppTheme.error),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _updateService.error!,
                    style: TextStyle(
                      fontSize: 12,
                      color: AppTheme.error,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
        if (_updateService.lastUpdateData.isNotEmpty) ...[
          const SizedBox(height: 12),
          _buildLastUpdateSummary(),
        ],
      ],
    );
  }

  Widget _buildDetailRow({
    required IconData icon,
    required String label,
    required String value,
  }) {
    return Row(
      children: [
        Icon(icon, size: 16, color: Colors.grey[600]),
        const SizedBox(width: 8),
        Text(
          '$label:',
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
        const Spacer(),
        Text(
          value,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  Widget _buildLastUpdateSummary() {
    final data = _updateService.lastUpdateData;
    final totalFloats = data['totalFloats'] ?? 0;
    final totalProfiles = data['totalProfiles'] ?? 0;
    final newFloats = data['newFloats'] ?? 0;
    final newProfiles = data['newProfiles'] ?? 0;

    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: AppTheme.success.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: AppTheme.success.withValues(alpha: 0.3)),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Icon(Icons.update, size: 16, color: AppTheme.success),
              const SizedBox(width: 8),
              Text(
                'Latest Update Summary',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.success,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildSummaryItem('Total Floats', totalFloats.toString()),
              _buildSummaryItem('Total Profiles', totalProfiles.toString()),
            ],
          ),
          if (newFloats > 0 || newProfiles > 0) ...[
            const SizedBox(height: 4),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildSummaryItem('New Floats', '+$newFloats', highlight: true),
                _buildSummaryItem('New Profiles', '+$newProfiles', highlight: true),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSummaryItem(String label, String value, {bool highlight = false}) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            color: highlight ? AppTheme.success : AppTheme.primaryBlue,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 10,
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }

  Widget _buildControls() {
    return Row(
      children: [
        if (_updateService.isRunning)
          OutlinedButton.icon(
            onPressed: () => _updateService.stop(),
            icon: const Icon(Icons.pause),
            label: const Text('Stop'),
          )
        else
          ElevatedButton.icon(
            onPressed: () => _updateService.start(),
            icon: const Icon(Icons.play_arrow),
            label: const Text('Start'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryBlue,
              foregroundColor: Colors.white,
            ),
          ),
        const SizedBox(width: 8),
        OutlinedButton.icon(
          onPressed: _updateService.status == DataUpdateStatus.updating
              ? null
              : () => _updateService.forceUpdate(),
          icon: const Icon(Icons.refresh),
          label: const Text('Update Now'),
        ),
        const Spacer(),
        IconButton(
          onPressed: () => _showSettingsDialog(),
          icon: const Icon(Icons.settings),
          tooltip: 'Update Settings',
        ),
      ],
    );
  }

  Widget _buildActionButton() {
    if (_updateService.status == DataUpdateStatus.updating ||
        _updateService.status == DataUpdateStatus.checking) {
      return const SizedBox(
        width: 20,
        height: 20,
        child: CircularProgressIndicator(strokeWidth: 2),
      );
    }

    return IconButton(
      onPressed: () => _updateService.forceUpdate(),
      icon: const Icon(Icons.refresh),
      tooltip: 'Refresh Data',
      iconSize: 20,
    );
  }

  Color _getStatusColor() {
    switch (_updateService.status) {
      case DataUpdateStatus.idle:
        return Colors.grey;
      case DataUpdateStatus.checking:
      case DataUpdateStatus.updating:
        return AppTheme.primaryBlue;
      case DataUpdateStatus.success:
        return AppTheme.success;
      case DataUpdateStatus.error:
        return AppTheme.error;
    }
  }

  void _showSettingsDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Data Update Settings'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.schedule),
              title: const Text('Update Interval'),
              subtitle: Text('${_updateService.updateInterval.inMinutes} minutes'),
              trailing: DropdownButton<int>(
                value: _updateService.updateInterval.inMinutes,
                items: [5, 15, 30, 60, 120].map((minutes) {
                  return DropdownMenuItem(
                    value: minutes,
                    child: Text('$minutes min'),
                  );
                }).toList(),
                onChanged: (value) {
                  if (value != null) {
                    _updateService.setUpdateInterval(Duration(minutes: value));
                    setState(() {});
                  }
                },
              ),
            ),
            SwitchListTile(
              secondary: const Icon(Icons.auto_mode),
              title: const Text('Auto Update'),
              subtitle: const Text('Automatically check for new data'),
              value: _updateService.isRunning,
              onChanged: (value) {
                if (value) {
                  _updateService.start();
                } else {
                  _updateService.stop();
                }
                setState(() {});
              },
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
}
