import 'package:flutter/material.dart';
import '../../themes/app_theme.dart';

class DataFilterCriteria {
  // Geographic bounds
  double? minLatitude;
  double? maxLatitude;
  double? minLongitude;
  double? maxLongitude;
  
  // Temporal bounds
  DateTime? startDate;
  DateTime? endDate;
  
  // Depth bounds
  double? minDepth;
  double? maxDepth;
  
  // Parameter selection
  List<String> selectedParameters = ['temperature'];
  
  // Float selection
  List<String>? selectedFloats;
  String? floatStatus; // 'active', 'inactive', null for all
  
  // Data quality
  List<String> qualityFlags = ['good']; // 'good', 'questionable', 'bad'

  DataFilterCriteria();

  Map<String, dynamic> toMap() {
    return {
      'geographic_bounds': {
        if (minLatitude != null) 'min_lat': minLatitude,
        if (maxLatitude != null) 'max_lat': maxLatitude,
        if (minLongitude != null) 'min_lon': minLongitude,
        if (maxLongitude != null) 'max_lon': maxLongitude,
      },
      'temporal_range': {
        if (startDate != null) 'start_date': startDate!.toIso8601String(),
        if (endDate != null) 'end_date': endDate!.toIso8601String(),
      },
      'depth_range': {
        if (minDepth != null) 'min_depth': minDepth,
        if (maxDepth != null) 'max_depth': maxDepth,
      },
      'parameters': selectedParameters,
      if (selectedFloats != null) 'float_ids': selectedFloats,
      if (floatStatus != null) 'float_status': floatStatus,
      'quality_flags': qualityFlags,
    };
  }

  bool get hasActiveFilters {
    return minLatitude != null ||
           maxLatitude != null ||
           minLongitude != null ||
           maxLongitude != null ||
           startDate != null ||
           endDate != null ||
           minDepth != null ||
           maxDepth != null ||
           selectedParameters.isNotEmpty ||
           (selectedFloats?.isNotEmpty ?? false) ||
           floatStatus != null ||
           qualityFlags.length != 1 || qualityFlags.first != 'good';
  }

  void clear() {
    minLatitude = null;
    maxLatitude = null;
    minLongitude = null;
    maxLongitude = null;
    startDate = null;
    endDate = null;
    minDepth = null;
    maxDepth = null;
    selectedParameters = ['temperature'];
    selectedFloats = null;
    floatStatus = null;
    qualityFlags = ['good'];
  }
}

class DataFilterPanel extends StatefulWidget {
  final DataFilterCriteria initialCriteria;
  final Function(DataFilterCriteria) onFiltersChanged;
  final bool isExpanded;

  const DataFilterPanel({
    super.key,
    required this.initialCriteria,
    required this.onFiltersChanged,
    this.isExpanded = false,
  });

  @override
  State<DataFilterPanel> createState() => _DataFilterPanelState();
}

class _DataFilterPanelState extends State<DataFilterPanel> {
  late DataFilterCriteria _criteria;
  bool _isExpanded = false;
  
  final List<String> _availableParameters = [
    'temperature',
    'salinity',
    'pressure',
    'oxygen',
  ];
  
  final List<String> _qualityOptions = ['good', 'questionable', 'bad'];
  final List<String> _statusOptions = ['active', 'inactive'];

  @override
  void initState() {
    super.initState();
    _criteria = widget.initialCriteria;
    _isExpanded = widget.isExpanded;
  }

  void _updateCriteria() {
    widget.onFiltersChanged(_criteria);
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(),
          if (_isExpanded) _buildFilterContent(),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return InkWell(
      onTap: () {
        setState(() {
          _isExpanded = !_isExpanded;
        });
      },
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          children: [
            Icon(
              Icons.filter_list,
              color: AppTheme.primaryBlue,
              size: 24,
            ),
            const SizedBox(width: 8),
            Text(
              'Data Filters',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: AppTheme.primaryBlue,
              ),
            ),
            const SizedBox(width: 8),
            if (_criteria.hasActiveFilters)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: AppTheme.accent,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Text(
                  'Active',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            const Spacer(),
            if (_criteria.hasActiveFilters)
              TextButton(
                onPressed: () {
                  setState(() {
                    _criteria.clear();
                  });
                  _updateCriteria();
                },
                child: const Text('Clear All'),
              ),
            Icon(
              _isExpanded ? Icons.expand_less : Icons.expand_more,
              color: AppTheme.primaryBlue,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilterContent() {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildGeographicFilters(),
          const SizedBox(height: 16),
          _buildTemporalFilters(),
          const SizedBox(height: 16),
          _buildDepthFilters(),
          const SizedBox(height: 16),
          _buildParameterFilters(),
          const SizedBox(height: 16),
          _buildFloatFilters(),
          const SizedBox(height: 16),
          _buildQualityFilters(),
          const SizedBox(height: 16),
          _buildApplyButton(),
        ],
      ),
    );
  }

  Widget _buildGeographicFilters() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.public, size: 18, color: AppTheme.primaryBlue),
            const SizedBox(width: 8),
            Text(
              'Geographic Bounds',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: AppTheme.primaryBlue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                decoration: const InputDecoration(
                  labelText: 'Min Latitude',
                  hintText: '-90.0',
                  border: OutlineInputBorder(),
                ),
                initialValue: _criteria.minLatitude?.toString(),
                keyboardType: TextInputType.number,
                onChanged: (value) {
                  _criteria.minLatitude = double.tryParse(value);
                },
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextFormField(
                decoration: const InputDecoration(
                  labelText: 'Max Latitude',
                  hintText: '90.0',
                  border: OutlineInputBorder(),
                ),
                initialValue: _criteria.maxLatitude?.toString(),
                keyboardType: TextInputType.number,
                onChanged: (value) {
                  _criteria.maxLatitude = double.tryParse(value);
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                decoration: const InputDecoration(
                  labelText: 'Min Longitude',
                  hintText: '-180.0',
                  border: OutlineInputBorder(),
                ),
                initialValue: _criteria.minLongitude?.toString(),
                keyboardType: TextInputType.number,
                onChanged: (value) {
                  _criteria.minLongitude = double.tryParse(value);
                },
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextFormField(
                decoration: const InputDecoration(
                  labelText: 'Max Longitude',
                  hintText: '180.0',
                  border: OutlineInputBorder(),
                ),
                initialValue: _criteria.maxLongitude?.toString(),
                keyboardType: TextInputType.number,
                onChanged: (value) {
                  _criteria.maxLongitude = double.tryParse(value);
                },
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildTemporalFilters() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.calendar_today, size: 18, color: AppTheme.primaryBlue),
            const SizedBox(width: 8),
            Text(
              'Date Range',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: AppTheme.primaryBlue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _selectStartDate(),
                icon: const Icon(Icons.date_range),
                label: Text(_criteria.startDate?.toString().split(' ')[0] ?? 'Start Date'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _selectEndDate(),
                icon: const Icon(Icons.date_range),
                label: Text(_criteria.endDate?.toString().split(' ')[0] ?? 'End Date'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildDepthFilters() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.waves, size: 18, color: AppTheme.primaryBlue),
            const SizedBox(width: 8),
            Text(
              'Depth Range (meters)',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: AppTheme.primaryBlue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                decoration: const InputDecoration(
                  labelText: 'Min Depth',
                  hintText: '0',
                  border: OutlineInputBorder(),
                ),
                initialValue: _criteria.minDepth?.toString(),
                keyboardType: TextInputType.number,
                onChanged: (value) {
                  _criteria.minDepth = double.tryParse(value);
                },
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextFormField(
                decoration: const InputDecoration(
                  labelText: 'Max Depth',
                  hintText: '2000',
                  border: OutlineInputBorder(),
                ),
                initialValue: _criteria.maxDepth?.toString(),
                keyboardType: TextInputType.number,
                onChanged: (value) {
                  _criteria.maxDepth = double.tryParse(value);
                },
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildParameterFilters() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.science, size: 18, color: AppTheme.primaryBlue),
            const SizedBox(width: 8),
            Text(
              'Parameters',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: AppTheme.primaryBlue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: _availableParameters.map((parameter) {
            final isSelected = _criteria.selectedParameters.contains(parameter);
            return FilterChip(
              label: Text(parameter.toUpperCase()),
              selected: isSelected,
              onSelected: (selected) {
                setState(() {
                  if (selected) {
                    _criteria.selectedParameters.add(parameter);
                  } else {
                    _criteria.selectedParameters.remove(parameter);
                  }
                });
              },
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildFloatFilters() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.sensors, size: 18, color: AppTheme.primaryBlue),
            const SizedBox(width: 8),
            Text(
              'Float Status',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: AppTheme.primaryBlue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: [
            FilterChip(
              label: const Text('All Floats'),
              selected: _criteria.floatStatus == null,
              onSelected: (selected) {
                if (selected) {
                  setState(() {
                    _criteria.floatStatus = null;
                  });
                }
              },
            ),
            ..._statusOptions.map((status) {
              final isSelected = _criteria.floatStatus == status;
              return FilterChip(
                label: Text(status.toUpperCase()),
                selected: isSelected,
                onSelected: (selected) {
                  setState(() {
                    _criteria.floatStatus = selected ? status : null;
                  });
                },
              );
            }),
          ],
        ),
      ],
    );
  }

  Widget _buildQualityFilters() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.verified, size: 18, color: AppTheme.primaryBlue),
            const SizedBox(width: 8),
            Text(
              'Data Quality',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: AppTheme.primaryBlue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          children: _qualityOptions.map((quality) {
            final isSelected = _criteria.qualityFlags.contains(quality);
            return FilterChip(
              label: Text(quality.toUpperCase()),
              selected: isSelected,
              onSelected: (selected) {
                setState(() {
                  if (selected) {
                    _criteria.qualityFlags.add(quality);
                  } else {
                    _criteria.qualityFlags.remove(quality);
                  }
                });
              },
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildApplyButton() {
    return Row(
      children: [
        Expanded(
          child: ElevatedButton(
            onPressed: _updateCriteria,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryBlue,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 12),
            ),
            child: const Text(
              'Apply Filters',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _selectStartDate() async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _criteria.startDate ?? DateTime.now().subtract(const Duration(days: 30)),
      firstDate: DateTime(2020, 1, 1),
      lastDate: DateTime.now(),
    );
    
    if (picked != null) {
      setState(() {
        _criteria.startDate = picked;
      });
    }
  }

  Future<void> _selectEndDate() async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _criteria.endDate ?? DateTime.now(),
      firstDate: _criteria.startDate ?? DateTime(2020, 1, 1),
      lastDate: DateTime.now(),
    );
    
    if (picked != null) {
      setState(() {
        _criteria.endDate = picked;
      });
    }
  }
}
