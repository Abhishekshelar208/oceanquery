import 'package:flutter/material.dart';
import 'dart:math' as math;

class RadarChartWidget extends StatefulWidget {
  final String title;
  final List<double> values;
  final List<String>? labels;
  final Color color;
  final double size;

  const RadarChartWidget({
    super.key,
    required this.title,
    required this.values,
    this.labels,
    this.color = const Color(0xFF00D4FF),
    this.size = 120,
  });

  @override
  State<RadarChartWidget> createState() => _RadarChartWidgetState();
}

class _RadarChartWidgetState extends State<RadarChartWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 1800),
      vsync: this,
    );
    _animation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.elasticOut),
    );
    _animationController.forward();
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  List<String> get chartLabels => widget.labels ?? ['Temp', 'Sal', 'O₂', 'pH'];

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Title
        Text(
          widget.title,
          style: const TextStyle(
            color: Colors.white70,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 8),
        
        // Radar Chart
        Expanded(
          child: AnimatedBuilder(
            animation: _animation,
            builder: (context, child) {
              return CustomPaint(
                painter: _RadarChartPainter(
                  values: widget.values,
                  labels: chartLabels,
                  color: widget.color,
                  animationValue: _animation.value,
                ),
                child: SizedBox(
                  width: widget.size,
                  height: widget.size,
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _RadarChartPainter extends CustomPainter {
  final List<double> values;
  final List<String> labels;
  final Color color;
  final double animationValue;

  _RadarChartPainter({
    required this.values,
    required this.labels,
    required this.color,
    required this.animationValue,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) / 2 - 20;
    final angleStep = 2 * math.pi / values.length;

    // Draw grid circles
    _drawGrid(canvas, center, radius);

    // Draw axes
    _drawAxes(canvas, center, radius, angleStep);

    // Draw labels
    _drawLabels(canvas, center, radius, angleStep);

    // Draw data polygon
    _drawDataPolygon(canvas, center, radius, angleStep);

    // Draw data points
    _drawDataPoints(canvas, center, radius, angleStep);
  }

  void _drawGrid(Canvas canvas, Offset center, double radius) {
    final gridPaint = Paint()
      ..color = Colors.white.withOpacity(0.1)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    // Draw concentric circles
    for (int i = 1; i <= 4; i++) {
      final gridRadius = radius * (i / 4);
      canvas.drawCircle(center, gridRadius, gridPaint);
    }
  }

  void _drawAxes(Canvas canvas, Offset center, double radius, double angleStep) {
    final axisPaint = Paint()
      ..color = Colors.white.withOpacity(0.2)
      ..strokeWidth = 1;

    for (int i = 0; i < values.length; i++) {
      final angle = i * angleStep - math.pi / 2;
      final endPoint = Offset(
        center.dx + radius * math.cos(angle),
        center.dy + radius * math.sin(angle),
      );
      canvas.drawLine(center, endPoint, axisPaint);
    }
  }

  void _drawLabels(Canvas canvas, Offset center, double radius, double angleStep) {
    for (int i = 0; i < values.length; i++) {
      final angle = i * angleStep - math.pi / 2;
      final labelRadius = radius + 15;
      final labelPoint = Offset(
        center.dx + labelRadius * math.cos(angle),
        center.dy + labelRadius * math.sin(angle),
      );

      final textSpan = TextSpan(
        text: labels[i],
        style: const TextStyle(
          color: Colors.white54,
          fontSize: 10,
          fontWeight: FontWeight.w500,
        ),
      );

      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
        textAlign: TextAlign.center,
      );

      textPainter.layout();
      
      final textOffset = Offset(
        labelPoint.dx - textPainter.width / 2,
        labelPoint.dy - textPainter.height / 2,
      );
      
      textPainter.paint(canvas, textOffset);
    }
  }

  void _drawDataPolygon(Canvas canvas, Offset center, double radius, double angleStep) {
    final path = Path();
    final fillPaint = Paint()
      ..color = color.withOpacity(0.2 * animationValue)
      ..style = PaintingStyle.fill;

    final strokePaint = Paint()
      ..color = color.withOpacity(animationValue)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;

    bool isFirst = true;
    for (int i = 0; i < values.length; i++) {
      final angle = i * angleStep - math.pi / 2;
      final value = values[i] / 100; // Normalize to 0-1
      final animatedValue = value * animationValue;
      final point = Offset(
        center.dx + radius * animatedValue * math.cos(angle),
        center.dy + radius * animatedValue * math.sin(angle),
      );

      if (isFirst) {
        path.moveTo(point.dx, point.dy);
        isFirst = false;
      } else {
        path.lineTo(point.dx, point.dy);
      }
    }
    path.close();

    // Draw filled polygon
    canvas.drawPath(path, fillPaint);

    // Draw border
    canvas.drawPath(path, strokePaint);
  }

  void _drawDataPoints(Canvas canvas, Offset center, double radius, double angleStep) {
    for (int i = 0; i < values.length; i++) {
      final angle = i * angleStep - math.pi / 2;
      final value = values[i] / 100; // Normalize to 0-1
      final animatedValue = value * animationValue;
      final point = Offset(
        center.dx + radius * animatedValue * math.cos(angle),
        center.dy + radius * animatedValue * math.sin(angle),
      );

      // Glow effect
      final glowPaint = Paint()
        ..color = color.withOpacity(0.4 * animationValue)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);

      canvas.drawCircle(point, 6, glowPaint);

      // Main dot
      final dotPaint = Paint()
        ..color = color.withOpacity(animationValue)
        ..style = PaintingStyle.fill;

      canvas.drawCircle(point, 4, dotPaint);

      // Inner highlight
      final innerPaint = Paint()
        ..color = Colors.white.withOpacity(0.8 * animationValue)
        ..style = PaintingStyle.fill;

      canvas.drawCircle(point, 2, innerPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _RadarChartPainter oldDelegate) {
    return oldDelegate.animationValue != animationValue ||
           oldDelegate.values != values ||
           oldDelegate.color != color;
  }
}
