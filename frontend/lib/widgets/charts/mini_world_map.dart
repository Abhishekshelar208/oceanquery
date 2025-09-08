import 'package:flutter/material.dart';
import 'dart:math' as math;

class MiniWorldMap extends StatefulWidget {
  const MiniWorldMap({super.key});

  @override
  State<MiniWorldMap> createState() => _MiniWorldMapState();
}

class _MiniWorldMapState extends State<MiniWorldMap>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );
    _animation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeInOut),
    );
    _animationController.forward();
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return CustomPaint(
          painter: _WorldMapPainter(animationValue: _animation.value),
          child: Container(),
        );
      },
    );
  }
}

class _WorldMapPainter extends CustomPainter {
  final double animationValue;

  _WorldMapPainter({required this.animationValue});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFF2A4A5A)
      ..style = PaintingStyle.fill;

    final borderPaint = Paint()
      ..color = const Color(0xFF3A5A6A)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    // Draw simplified continents
    _drawContinents(canvas, size, paint, borderPaint);

    // Draw ARGO float locations as glowing dots
    _drawFloatLocations(canvas, size);

    // Draw data connections
    _drawDataConnections(canvas, size);
  }

  void _drawContinents(Canvas canvas, Size size, Paint paint, Paint borderPaint) {
    final width = size.width;
    final height = size.height;

    // North America (simplified)
    final northAmerica = Path();
    northAmerica.moveTo(width * 0.15, height * 0.2);
    northAmerica.lineTo(width * 0.25, height * 0.15);
    northAmerica.lineTo(width * 0.35, height * 0.25);
    northAmerica.lineTo(width * 0.28, height * 0.45);
    northAmerica.lineTo(width * 0.22, height * 0.5);
    northAmerica.lineTo(width * 0.12, height * 0.35);
    northAmerica.close();

    canvas.drawPath(northAmerica, paint);
    canvas.drawPath(northAmerica, borderPaint);

    // South America (simplified)
    final southAmerica = Path();
    southAmerica.moveTo(width * 0.22, height * 0.52);
    southAmerica.lineTo(width * 0.28, height * 0.48);
    southAmerica.lineTo(width * 0.32, height * 0.65);
    southAmerica.lineTo(width * 0.25, height * 0.82);
    southAmerica.lineTo(width * 0.20, height * 0.75);
    southAmerica.lineTo(width * 0.18, height * 0.60);
    southAmerica.close();

    canvas.drawPath(southAmerica, paint);
    canvas.drawPath(southAmerica, borderPaint);

    // Europe/Africa (simplified)
    final europeAfrica = Path();
    europeAfrica.moveTo(width * 0.45, height * 0.15);
    europeAfrica.lineTo(width * 0.55, height * 0.18);
    europeAfrica.lineTo(width * 0.58, height * 0.35);
    europeAfrica.lineTo(width * 0.52, height * 0.75);
    europeAfrica.lineTo(width * 0.48, height * 0.70);
    europeAfrica.lineTo(width * 0.42, height * 0.45);
    europeAfrica.lineTo(width * 0.40, height * 0.25);
    europeAfrica.close();

    canvas.drawPath(europeAfrica, paint);
    canvas.drawPath(europeAfrica, borderPaint);

    // Asia (simplified)
    final asia = Path();
    asia.moveTo(width * 0.58, height * 0.12);
    asia.lineTo(width * 0.85, height * 0.15);
    asia.lineTo(width * 0.82, height * 0.45);
    asia.lineTo(width * 0.75, height * 0.35);
    asia.lineTo(width * 0.62, height * 0.38);
    asia.lineTo(width * 0.55, height * 0.18);
    asia.close();

    canvas.drawPath(asia, paint);
    canvas.drawPath(asia, borderPaint);

    // Australia (simplified)
    final australia = Path();
    australia.moveTo(width * 0.72, height * 0.65);
    australia.lineTo(width * 0.82, height * 0.68);
    australia.lineTo(width * 0.80, height * 0.78);
    australia.lineTo(width * 0.70, height * 0.75);
    australia.close();

    canvas.drawPath(australia, paint);
    canvas.drawPath(australia, borderPaint);
  }

  void _drawFloatLocations(Canvas canvas, Size size) {
    final floatLocations = [
      // Atlantic Ocean
      Offset(size.width * 0.35, size.height * 0.35),
      Offset(size.width * 0.38, size.height * 0.55),
      Offset(size.width * 0.32, size.height * 0.65),
      
      // Pacific Ocean
      Offset(size.width * 0.15, size.height * 0.45),
      Offset(size.width * 0.85, size.height * 0.40),
      Offset(size.width * 0.90, size.height * 0.55),
      Offset(size.width * 0.78, size.height * 0.60),
      
      // Indian Ocean
      Offset(size.width * 0.65, size.height * 0.55),
      Offset(size.width * 0.68, size.height * 0.45),
      Offset(size.width * 0.62, size.height * 0.65),
      
      // Arctic Ocean
      Offset(size.width * 0.45, size.height * 0.08),
      Offset(size.width * 0.65, size.height * 0.05),
    ];

    for (int i = 0; i < floatLocations.length; i++) {
      final location = floatLocations[i];
      final animatedRadius = (3 + math.sin(animationValue * math.pi * 2 + i * 0.5)) * 2;
      
      // Glow effect
      final glowPaint = Paint()
        ..color = const Color(0xFF00D4FF).withOpacity(0.3 * animationValue)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);
      
      canvas.drawCircle(location, animatedRadius + 3, glowPaint);
      
      // Main dot
      final dotPaint = Paint()
        ..color = const Color(0xFF00D4FF).withOpacity(animationValue)
        ..style = PaintingStyle.fill;
      
      canvas.drawCircle(location, animatedRadius, dotPaint);
      
      // Center highlight
      final centerPaint = Paint()
        ..color = Colors.white.withOpacity(0.8 * animationValue)
        ..style = PaintingStyle.fill;
      
      canvas.drawCircle(location, animatedRadius * 0.3, centerPaint);
    }
  }

  void _drawDataConnections(Canvas canvas, Size size) {
    final connectionPaint = Paint()
      ..color = const Color(0xFF00D4FF).withOpacity(0.2 * animationValue)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;

    // Draw some connection lines between float locations
    final connections = [
      [Offset(size.width * 0.35, size.height * 0.35), Offset(size.width * 0.38, size.height * 0.55)],
      [Offset(size.width * 0.65, size.height * 0.55), Offset(size.width * 0.78, size.height * 0.60)],
      [Offset(size.width * 0.85, size.height * 0.40), Offset(size.width * 0.90, size.height * 0.55)],
    ];

    for (final connection in connections) {
      final path = Path();
      path.moveTo(connection[0].dx, connection[0].dy);
      
      // Create a curved line
      final controlPoint = Offset(
        (connection[0].dx + connection[1].dx) / 2,
        math.min(connection[0].dy, connection[1].dy) - 20,
      );
      
      path.quadraticBezierTo(
        controlPoint.dx,
        controlPoint.dy,
        connection[1].dx,
        connection[1].dy,
      );
      
      canvas.drawPath(path, connectionPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _WorldMapPainter oldDelegate) {
    return oldDelegate.animationValue != animationValue;
  }
}
