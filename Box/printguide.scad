t = 25;
h = 60 - 25;


difference()
{
    union() {
        cube([2, 20, 120]);
        translate([-5, 0,0]) cube([5, 1, 120]);
        translate([0,1,0]) rotate([0,0,-54])
            cube([2, 43, 120]);
    }
    translate([-5,-5,-5])
        cube([10,5,130]);
    
    translate([0,10,0]) {
        rotate([0,90,0]) {
            translate([-15, 0, -1]) cylinder(d=3.5, h=5, $fn=20);
            translate([-120+15, 0, -1]) cylinder(d=3.5, h=5, $fn=20);

            translate([-15, 0, 5]) cylinder(d=8, h=20, $fn=20);
            translate([-120+15, 0, 5]) cylinder(d=8, h=20, $fn=20);
        }
    }
}
