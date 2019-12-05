d1 = 25;
d2 = 23;
d3 = 35;
h = 10;

difference() {
    union() {
        cylinder(d=d1, h=h, $fn=100);
        cylinder(d=d3, h=1, $fn=100);
    }
    translate([0,0,-5]) cylinder(d=d2, h=h+10, $fn=100);    
}