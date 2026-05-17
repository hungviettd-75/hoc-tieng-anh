import 'package:flutter/material.dart';
import 'package:confetti/confetti.dart';

class ConfettiOverlay extends StatefulWidget {
  final Widget child;
  final ConfettiController controller;

  const ConfettiOverlay({
    Key? key,
    required this.child,
    required this.controller,
  }) : super(key: key);

  @override
  State<ConfettiOverlay> createState() => _ConfettiOverlayState();
}

class _ConfettiOverlayState extends State<ConfettiOverlay> {
  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        widget.child,
        Align(
          alignment: Alignment.topCenter,
          child: ConfettiWidget(
            confettiController: widget.controller,
            blastDirectionality: BlastDirectionality.explosive,
            shouldLoop: false,
            colors: const [
              Colors.green,
              Colors.blue,
              Colors.pink,
              Colors.orange,
              Colors.purple,
              Colors.yellow,
            ],
            numberOfParticles: 20,
            gravity: 0.1,
          ),
        ),
      ],
    );
  }
}
