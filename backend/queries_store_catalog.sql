

psql -d nombre_base_datos -U nombre_usuario

\dt
select * from products;
delete from categories where id>20;
delete from categories where name='Clothing';
UPDATE colors SET name = 'violeta/morado' WHERE id=74;




select name, code, stock, price, ubicacion from products;

select name, code, stock, price, ubicacion from products where ubicacion like '%Caja 1';
select name, code, stock, price, ubicacion from products where ubicacion like '%caja 1';
select name, code, stock, price, ubicacion from products where ubicacion like '%caja1%';
select name, code, stock, price, ubicacion from products where ubicacion like 'estante blanco%';

update products set ubicacion = 'Caja 01' where ubicacion='Caja1';
update products set ubicacion = 'Caja 01' where ubicacion='caja1';
update products set ubicacion = 'Caja 01' where ubicacion='Caja 1';

select name, code, stock, price, ubicacion from products where ubicacion='Caja 3';
select name, code, stock, price, ubicacion from products where ubicacion='Caja3';
update products set ubicacion = 'Caja 03' where ubicacion='Caja3';
update products set ubicacion = 'Caja 03' where ubicacion='Caja 3';

select name, code, stock, price, ubicacion from products where ubicacion='Caja 2';
update products set ubicacion = 'Caja 02' where ubicacion='Caja 2';
select name, code, stock, price, ubicacion from products where ubicacion='Caja 02';

select name, code, stock, price, ubicacion from products where ubicacion='10';
update products set ubicacion = 'Caja 10' where ubicacion='10';
select name, code, stock, price, ubicacion from products where ubicacion='Caja 10';

select name, code, stock, price, ubicacion from products where ubicacion='13';
update products set ubicacion = 'Caja 13' where ubicacion='13';
select name, code, stock, price, ubicacion from products where ubicacion='Caja 13';

select name, code, stock, price, ubicacion from products where ubicacion='Estante1';
update products set ubicacion = 'Estante 1' where ubicacion='Estante1';
select name, code, stock, price, ubicacion from products where ubicacion='Estante 1';

select name, code, stock, price, ubicacion from products where ubicacion='Caja7';
update products set ubicacion = 'Caja 7' where ubicacion='Caja7';
select name, code, stock, price, ubicacion from products where ubicacion='Caja 7';

select name, code, stock, price, ubicacion from products where ubicacion='Caja 4';
update products set ubicacion = 'Caja 04' where ubicacion='Caja 4';
select name, code, stock, price, ubicacion from products where ubicacion='Caja 04';

select name, code, stock, price, ubicacion from products where ubicacion='Caja 5';
update products set ubicacion = 'Caja 05' where ubicacion='Caja 5';
select name, code, stock, price, ubicacion from products where ubicacion='Caja 05';

select name, code, stock, price, ubicacion from products where ubicacion='24';
update products set ubicacion = 'Caja 24' where ubicacion='24';
select name, code, stock, price, ubicacion from products where ubicacion='Caja 24';

select name, code, stock, price, ubicacion from products where ubicacion='26';
update products set ubicacion = 'Caja 26' where ubicacion='26';
select name, code, stock, price, ubicacion from products where ubicacion='Caja 26';

select name, code, stock, price, ubicacion from products where ubicacion='27';
update products set ubicacion = 'Caja 27' where ubicacion='27';
select name, code, stock, price, ubicacion from products where ubicacion='Caja 27';


update products set ubicacion = 'Caja 01' where ubicacion='Caja 1';
update products set ubicacion = 'Caja 9' where ubicacion='Caja  9';
update products set ubicacion = 'Caja 06' where ubicacion='Caja 6';
update products set ubicacion = 'Caja 18' where ubicacion='18';
update products set ubicacion = 'Estante blanco' where ubicacion='estante blanco';


select sum(stock*price) from products;
select ubicacion, sum(stock*price) from products group by ubicacion;


WITH per_product AS (
    SELECT
        p.id, p.name, p.code, p.price, p.stock,
        (SELECT MIN(c.name)
           FROM product_categories pc
           JOIN categories c ON c.id = pc.category_id
          WHERE pc.product_id = p.id) AS category,
        (SELECT MIN(cl.name)
           FROM product_colors pcl
           JOIN colors cl ON cl.id = pcl.color_id
          WHERE pcl.product_id = p.id) AS color
    FROM products p
    WHERE p.stock > 0
),
category_counts AS (
    SELECT category, COUNT(*) AS product_count
    FROM per_product
    WHERE category IS NOT NULL
    GROUP BY category
)
SELECT
    pp.id, pp.name, pp.code, pp.price, pp.stock,
    pp.category, pp.color,
    COALESCE(cc.product_count, 0) AS category_count
FROM per_product pp
LEFT JOIN category_counts cc ON cc.category = pp.category
ORDER BY category_count DESC, pp.category ASC, pp.color ASC, pp.stock ASC;


