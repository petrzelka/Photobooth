difference() { 
    X();
    
    translate([0,0,30])
    union() {
        translate([-12.5/2,-15,-3]) cube([12.5, 30, 5]);
        translate([-18.8/2,-15,-3]) cube([18.8, 30, 2]);
    }
    
    translate([35,12,0]) M4();
    translate([-35,12,0]) M4();

    translate([30,-15,0]) M4();
    translate([-30,-15,0]) M4();
 
    translate([0,0,-4.5]) scale([0.7, 0.7, 0.9]) X();
    
    translate([0,0,17]) rotate([90,0,0]) cylinder(d=10, h=20, $fn=50);
}

module X() {
    difference() {
        hull() {
            translate([0,0,0]) scale([1,0.6,1]) cylinder(r=50, h=5, $fn=100);
            translate([0,10,20]) cube([25,25,20], center=true);
        }

        translate([0,5,34.5]) scale([1,0.7,1]) {
            rotate_extrude(convexity = 10, $fn = 100)
            translate([50, 0, 0])
            circle(r = 30, $fn = 100);
        }
    }
}

module M4() {
    translate([0,0,4]) cylinder(d=8, h=20, $fn=20);
    translate([0,0,0]) cylinder(d1=0, d2=8, h=4.1, $fn=20);
    translate([0,0,-18]) cylinder(d=4, h=20, $fn=20);
}