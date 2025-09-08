import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../themes/app_theme.dart';

class ArgoMap extends StatefulWidget {
  const ArgoMap({super.key});

  @override
  State<ArgoMap> createState() => _ArgoMapState();
}

class _ArgoMapState extends State<ArgoMap> {
  final MapController _mapController = MapController();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: FlutterMap(
          mapController: _mapController,
          options: const MapOptions(
            initialCenter: LatLng(15.0, 75.0), // Indian Ocean
            initialZoom: 5.0,
            minZoom: 2.0,
            maxZoom: 18.0,
            interactionOptions: InteractionOptions(
              enableMultiFingerGestureRace: true,
            ),
          ),
          children: [
            // Base map layer
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.oceanquery.app',
              maxZoom: 18,
            ),
            
            // ARGO float markers
            MarkerLayer(
              markers: _generateFloatMarkers(),
            ),
            
            // Map attribution
            const SimpleAttributionWidget(
              source: Text('© OpenStreetMap'),
            ),
            
            // Custom controls
            Positioned(
              top: 10,
              right: 10,
              child: Column(
                children: [
                  Container(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(8),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.1),
                          blurRadius: 4,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: Column(
                      children: [
                        IconButton(
                          icon: const Icon(Icons.add),
                          onPressed: () {
                            _mapController.move(
                              _mapController.camera.center,
                              _mapController.camera.zoom + 1,
                            );
                          },
                          tooltip: 'Zoom in',
                        ),
                        IconButton(
                          icon: const Icon(Icons.remove),
                          onPressed: () {
                            _mapController.move(
                              _mapController.camera.center,
                              _mapController.camera.zoom - 1,
                            );
                          },
                          tooltip: 'Zoom out',
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(4),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.1),
                          blurRadius: 4,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: Text(
                      '47 Floats',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.primaryBlue,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            
            // Legend
            Positioned(
              bottom: 30,
              left: 10,
              child: Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.9),
                  borderRadius: BorderRadius.circular(8),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.1),
                      blurRadius: 4,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'ARGO Floats',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 12,
                          height: 12,
                          decoration: const BoxDecoration(
                            color: AppTheme.success,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 4),
                        const Text('Active', style: TextStyle(fontSize: 10)),
                      ],
                    ),
                    const SizedBox(height: 2),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 12,
                          height: 12,
                          decoration: const BoxDecoration(
                            color: AppTheme.warning,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 4),
                        const Text('Inactive', style: TextStyle(fontSize: 10)),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Marker> _generateFloatMarkers() {
    // Mock ARGO float locations in the Indian Ocean
    final floatData = [
      {'lat': 10.5, 'lon': 77.2, 'id': '2902755', 'active': true},
      {'lat': 8.3, 'lon': 73.1, 'id': '2902756', 'active': true},
      {'lat': 12.7, 'lon': 79.5, 'id': '2902757', 'active': false},
      {'lat': 6.1, 'lon': 80.2, 'id': '2902758', 'active': true},
      {'lat': 15.4, 'lon': 68.9, 'id': '2902759', 'active': true},
      {'lat': 9.8, 'lon': 76.3, 'id': '2902760', 'active': true},
      {'lat': 13.2, 'lon': 74.8, 'id': '2902761', 'active': false},
      {'lat': 7.6, 'lon': 78.7, 'id': '2902762', 'active': true},
    ];

    return floatData.map((data) {
      final isActive = data['active'] as bool;
      return Marker(
        point: LatLng(data['lat'] as double, data['lon'] as double),
        child: GestureDetector(
          onTap: () => _showFloatInfo(data['id'] as String, isActive),
          child: Container(
            width: 16,
            height: 16,
            decoration: BoxDecoration(
              color: isActive ? AppTheme.success : AppTheme.warning,
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white, width: 2),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.2),
                  blurRadius: 3,
                  offset: const Offset(0, 1),
                ),
              ],
            ),
            child: Icon(
              Icons.sensors,
              size: 8,
              color: Colors.white,
            ),
          ),
        ),
      );
    }).toList();
  }

  void _showFloatInfo(String floatId, bool isActive) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('ARGO Float $floatId'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.circle,
                  size: 12,
                  color: isActive ? AppTheme.success : AppTheme.warning,
                ),
                const SizedBox(width: 4),
                Text(
                  isActive ? 'Active' : 'Inactive',
                  style: TextStyle(
                    color: isActive ? AppTheme.success : AppTheme.warning,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text('Last transmission: ${isActive ? "2 hours ago" : "3 days ago"}'),
            const SizedBox(height: 4),
            Text('Profiles collected: ${isActive ? "1,247" : "892"}'),
            const SizedBox(height: 4),
            Text('Current depth: ${isActive ? "Surface" : "Unknown"}'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
          if (isActive)
            ElevatedButton(
              onPressed: () {
                Navigator.of(context).pop();
                // TODO: Navigate to detailed float data
              },
              child: const Text('View Data'),
            ),
        ],
      ),
    );
  }
}
